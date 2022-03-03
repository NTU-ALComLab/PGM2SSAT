from multiprocessing.sharedctypes import Value
import os
import itertools
from platform import node
import random
import re
import math
import sys
from unicodedata import numeric

# sys.setrecursionlimit(5000)


class Node:
    '''
    node for bayesian network
    '''

    def __init__(self, id, kind, name=None):
        self.id = id
        self.kind = kind    # chance, decision, utility
        if name is None:
            self.name = str(id)
        else:
            self.name = name

        self.num_states = 0
        self.states = []
        self.cpt = []       # state_comb x num_states for chance node
        self.vals = []      # state_comb x 1 for utility node

        self.parents = []
        self.children = []

        self.visit = False  # traversal
        self.finish_id = 0  # for topological sort
        self.dec_level = 0  # the decision level (number of decisions passed until utility node)

        self.uai_id = 0

        self.depend = True  # dependency with query
        # independent with decision but depedent on others (used in SDP query)
        self.not_depend_d = False

        self.component_label = 0   # label of connected components
        self.cared = True


class gNode:
    '''
    node for graph operation
    '''

    def __init__(self, node):
        self.id = node.id
        self.parents = [n.id for n in node.parents if n.depend]
        self.children = [n.id for n in node.children if n.depend]
        self.neighbors = self.parents + self.children


evid_query = ['PE', 'MPE', 'MAP', 'MEU']
map_query = ['MAP']
sdp_query = ['SDP']


class Network:
    def __init__(self, kind='', query='', causal=False):
        self.kind = kind    # BN (Bayesian network), ID (influence diagram)
        self.query = query  # PE, MPE, MAP, SDP for BN, MEU for ID
        self.causal = causal  # if causal, use intervention

        self.num_nodes = 0
        self.nodes = []
        self.id2node = {}
        self.name2node = {}
        self.copy_nodes = []

        self.minfill_order = []

        # for MEU in ID
        self.max_dec_level = 0
        self.level2dec = {}

        self.num_utils = 0
        self.utils = []
        self.id2util = {}
        self.super_util = None

        self.evids = []     # evidence of some variables (node_id, state)
        self.query_var = []  # query variables for MAP (node_id)

        self.finish_id = 0  # for topological sort

        # for SDP query
        self.dec_thr = 0.5
        self.dec = []       # d variable for SDP (node_id, state)
        self.unobserved = []    # H variables for SDP (node_id)

    def read(self, filename, evid_file='', query_file='', sdp_file=''):
        name, ext = os.path.splitext(filename)
        if len(evid_file) == 0:
            evid_file = filename + '.evid'
        if len(query_file) == 0:
            map_file = filename + '.map'
            query_file = filename + '.query'
        if len(sdp_file) == 0:
            sdp_file = filename + '.sdp'
            query_file = filename + '.query'

        if ext == '.uai':
            self.read_uai(filename)
        elif ext == '.erg':
            self.read_erg(filename)
        elif ext == '.bif':
            self.read_bif_bn(filename)
        elif ext == '.dne':
            self.read_dne_bn(filename)
        elif ext == '.limid':
            self.read_limid(filename)
        elif ext == '.cpt':
            self.read_cpt(filename)

        if self.query in evid_query:
            if os.path.isfile(evid_file):
                self.read_evid(evid_file)
                print('Find evidence file', evid_file)

        if self.query in map_query:
            if os.path.isfile(map_file):
                self.read_map(map_file)
                print('Find map file', map_file)
            elif os.path.isfile(query_file):
                self.read_map(query_file)
                print('Find map file', query_file)

        if self.query in sdp_query:
            if os.path.isfile(sdp_file):
                self.read_sdp(sdp_file)
                print('Find sdp file', sdp_file)
            elif os.path.isfile(query_file):
                self.read_sdp(query_file)
                print('Find sdp file', query_file)

    def read_uai(self, filename):
        f = open(filename, 'r')
        line = f.readline().strip()
        f.close()
        if line == 'ID':
            self.read_uai_id(filename)
        elif line == 'BAYES':
            self.read_uai_bn(filename)
        else:
            raise ValueError('Invalid type of network', line)

    def read_erg(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        self.num_nodes = int(lines[0])

        # each node has how many states
        pars = lines[1].strip().split()
        for i in range(self.num_nodes):
            n = Node(i, 'chance')
            n.num_states = int(pars[i])
            n.states = [j for j in range(n.num_states)]
            self.nodes.append(n)
            self.id2node[i] = n

        # each node has [incoming nodes]
        for i in range(self.num_nodes):
            pars = lines[2+i].strip().split()
            num_parents = int(pars[0])
            n = self.id2node[i]
            for j in range(num_parents):
                m = int(pars[j+1])
                p = self.id2node[m]
                n.parents.append(p)
                p.children.append(n)

        cpt_lino = 2 + self.num_nodes + 1
        for i in range(self.num_nodes):
            n = self.id2node[i]
            cpt_lino += 1
            num_vals = int(lines[cpt_lino])
            num_rows = int(num_vals / n.num_states)
            for j in range(num_rows):
                cpt_lino += 1
                pars = lines[cpt_lino].strip().split()
                vals = [float(p) for p in pars]
                n.cpt.append(vals)
            cpt_lino += 1

    def read_uai_bn(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        if lines[0].strip() != 'BAYES':
            print('Only accept Bayesian network')
            return

        self.num_nodes = int(lines[1])

        # each node has how many states
        pars = lines[2].strip().split()
        for i in range(self.num_nodes):
            n = Node(i, 'chance')
            n.num_states = int(pars[i])
            n.states = [j for j in range(n.num_states)]
            self.nodes.append(n)
            self.id2node[i] = n

        '''
            only consider the case that
            all nodes are listed and from 0 ~ n
        '''
        # each node has [incoming nodes]
        for i in range(self.num_nodes):
            pars = lines[4+i].strip().split()
            num_parents = int(pars[0]) - 1
            n = self.id2node[i]
            for j in range(num_parents):
                m = int(pars[j+1])
                p = self.id2node[m]
                n.parents.append(p)
                p.children.append(n)

        cpt_lino = 4 + self.num_nodes + 1
        for i in range(self.num_nodes):
            n = self.id2node[i]
            num_vals = int(lines[cpt_lino])
            num_rows = int(num_vals / n.num_states)
            for j in range(num_rows):
                cpt_lino += 1
                pars = lines[cpt_lino].strip().split()
                vals = [float(p) for p in pars]
                n.cpt.append(vals)
            cpt_lino += 2

    def read_uai_id(self, filename):
        id_file = filename.replace('.uai', '.id')
        pvo_file = filename.replace('.uai', '.pvo')

        f_id = open(id_file, 'r')
        lines = f_id.readlines()
        f_id.close()

        self.num_nodes = int(lines[0])
        node_types = lines[1].strip().split()
        num_relations = int(lines[2])
        relation_types = lines[3].strip().split()

        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        if lines[0].strip() != 'ID':
            print('Only accept ID, get', lines[0].strip())
            return

        # nodes
        assert self.num_nodes == int(lines[1])
        pars = lines[2].strip().split()
        for i in range(self.num_nodes):
            if node_types[i] == 'C':
                n = Node(i, 'chance')
            elif node_types[i] == 'D':
                n = Node(i, 'decision')
            else:
                raise ValueError('Unknown node type', node_types[i])
            n.num_states = int(pars[i])
            n.states = [j for j in range(n.num_states)]
            self.nodes.append(n)
            self.id2node[i] = n

        # relations
        assert num_relations == int(lines[3])
        table_ids = []  # the node id own the table
        for i in range(num_relations):
            lino = 4+i
            pars = lines[lino].strip().split()
            assert int(pars[0]) == (len(pars)-1)
            if relation_types[i] == 'P':
                cid = int(pars[-1])
                n = self.id2node[cid]
                for pid in pars[1:-1]:
                    p = self.id2node[int(pid)]
                    n.parents.append(p)
                    p.children.append(n)
                table_ids.append(cid)
            elif relation_types[i] == 'U':
                self.num_utils += 1
                id = self.num_nodes + self.num_utils + 1
                n = Node(id, 'utility')
                self.utils.append(n)
                self.id2util[id] = n
                for v in pars[1:]:
                    p = self.id2node[int(v)]
                    n.parents.append(p)
                table_ids.append(id)
            else:
                raise ValueError('Unknown relation type', relation_types[i])

        # cpts
        lino = num_relations + 5
        for cid in table_ids:
            n = self.id2node.get(cid)
            if n is None:
                n = self.id2util.get(cid)

            num_vals = int(lines[lino])
            vals = []
            for i in range(num_vals):
                lino += 1
                vals.append(float(lines[lino]))

            if n.kind == 'chance':
                num_col = n.num_states
                num_row = num_vals / num_col
                n.cpt = [vals[i:i+num_col] for i in range(0, num_vals, num_col)]
            elif n.kind == 'utility':
                n.vals = vals
            else:
                raise ValueError('Unknown node type', n.kind)
            lino += 2

        # decision
        f_pvo = open(pvo_file, 'r')
        lines = f_pvo.readlines()
        f_pvo.close()

        assert self.num_nodes == int(lines[0].strip(';\n'))
        num_alter = int(lines[1].strip(';\n'))
        dec_flag = False
        for i in range(num_alter):
            pars = lines[i+2].strip(';\n').split()
            if dec_flag == True:
                assert n.kind == 'decision'
                for id in pars:
                    p = self.id2node[int(id)]
                    p.children.append(n)
                    n.parents.append(p)
                dec_flag = False

            if len(pars) == 1:
                id = int(pars[0])
                n = self.id2node[id]
                if n.kind == 'decision':
                    dec_flag = True

    def read_limid(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        assert (lines[0].strip() == 'ID'), lines[0]

        self.num_nodes = int(lines[1].strip())

        par = lines[3].strip().split(' ')
        for i in range(self.num_nodes):
            if par[i] == 'c':
                n = Node(i, 'chance')
            elif par[i] == 'd':
                n = Node(i, 'decision')
            self.nodes.append(n)
            self.id2node[i] = n

        par = lines[2].strip().split(' ')
        for i in range(self.num_nodes):
            n = self.id2node[i]
            n.num_states = int(par[i])
            n.states = [j for j in range(n.num_states)]

        table_id = []

        num_relations = int(lines[5].strip())
        for i in range(num_relations):
            par = lines[6+i].strip().split(' ')
            if par[0] == 'd' or par[0] == 'p':
                id = int(par[-1])
                n = self.id2node[id]
                for v in par[2:-1]:
                    p = self.id2node[int(v)]
                    n.parents.append(p)
                    p.children.append(n)
                table_id.append(id)
            elif par[0] == 'u':
                self.num_utils += 1
                id = self.num_nodes + self.num_utils + 1
                n = Node(id, 'utility')
                self.utils.append(n)
                self.id2util[id] = n
                for v in par[2:]:
                    p = self.id2node[int(v)]
                    n.parents.append(p)
                table_id.append(id)

        lino = 5 + num_relations + 1
        for node_id in table_id:
            n = self.id2node.get(node_id)
            if n is None:
                n = self.id2util.get(node_id)
            lino += 1
            line = lines[lino]
            num_vals = int(line.strip())
            if n.kind == 'chance':
                num_rows = int(num_vals / n.num_states)
                assert (num_rows * n.num_states == num_vals), (num_rows, n.num_states, num_vals)
                for i in range(num_rows):
                    lino += 1
                    par = lines[lino].strip().split()
                    assert (len(par) == n.num_states), (len(par), n.num_states)
                    row_val = [float(par[j]) for j in range(n.num_states)]
                    n.cpt.append(row_val)
            elif n.kind == 'utility':
                for i in range(num_vals):
                    lino += 1
                    val = float(lines[lino].strip())
                    n.vals.append(val)
            elif n.kind == 'decision':
                assert(num_vals == 0), num_vals
            else:
                raise ValueError('%s node does not have table' % n.kind)

            lino += 1

    def read_bif_bn(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        n = None
        in_node = False
        in_table = False
        for line in lines:
            pars = line.strip().split()
            if pars[0] == 'variable':
                name = pars[1]
                n = Node(self.num_nodes, 'chance', name)
                self.nodes.append(n)
                self.name2node[name] = n
                self.num_nodes += 1
                in_node = True
            elif in_node is True:
                if pars[0] == '}':
                    in_node = False
                    continue
                n.num_states = int(pars[3])
                n.states = [s.strip(',') for s in pars[6:-1]]
                in_node = False
            elif pars[0] == 'probability':
                name = pars[2]
                n = self.name2node[name]
                in_table = True
                # has parent
                if pars[3] == '|':
                    for name in pars[4:-2]:
                        name = name.strip(',')
                        p = self.name2node[name]
                        n.parents.append(p)
                        p.children.append(n)
            elif in_table is True:
                if pars[0] == '}':
                    in_table = False
                    continue
                if pars[0] == 'table':
                    n.cpt = [[float(val.strip(',').strip(';')) for val in pars[1:]]]
                if pars[0][0] == '(':
                    i = 0
                    for par in pars:
                        i += 1
                        if par[-1] == ')':
                            break
                    row = []
                    for par in pars[i:]:
                        row.append(float(par.strip(',').strip(';')))
                    n.cpt.append(row)

    def read_dne_bn(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        flag = None
        for line in lines:
            pars = line.strip().split()

            if flag == 'probs':
                if pars[0][0] == '(':
                    cpt = []
                    for i, s in enumerate(pars):
                        s = re.sub(r'[(,);]', '', s)
                        cpt.append(float(s))
                        if (i+1) % n.num_states == 0:
                            n.cpt.append(cpt)
                            cpt = []
                else:
                    flag = None

            if len(pars) == 0:
                continue
            elif pars[0] == 'node':
                name = pars[1].strip('{')
                n = Node(self.num_nodes, 'chance', name=name)
                self.nodes.append(n)
                self.id2node[self.num_nodes] = n
                self.name2node[name] = n
                self.num_nodes += 1
            elif pars[0] == 'states':
                for s in pars[2:]:
                    s = re.sub(r'[(,);]', '', s)
                    n.states.append(s)
                    n.num_states += 1
            elif pars[0] == 'parents':
                for s in pars[2:]:
                    s = re.sub(r'[(,);]', '', s)
                    if len(s) > 0:
                        p = self.name2node[s]
                        n.parents.append(p)
                        p.children.append(n)
            elif pars[0] == 'probs':
                flag = 'probs'
                cpt = []
                for i, s in enumerate(pars[2:]):
                    s = re.sub(r'[(,);]', '', s)
                    cpt.append(float(s))
                    if (i+1) % n.num_states == 0:
                        n.cpt.append(cpt)
                        cpt = []

    def read_cpt(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        assert lines[0].strip() == 'CPT'

        self.num_nodes = 1
        n = Node(self.num_nodes, 'chance')
        n.num_states = int(lines[3].strip())
        row = []
        for i in range(n.num_states):
            val = float(lines[i+4].strip())
            row.append(val)
        n.cpt = [row]
        self.nodes.append(n)
        self.id2node[self.num_nodes] = n

    def read_evid(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        if lines[0].strip() == '/* Evidence */':
            num_evids = int(lines[1])
            for i in range(num_evids):
                pars = lines[2+i].strip().split()
                id = int(pars[0])
                state = int(pars[1])
                self.evids.append((id, state))
        else:
            pars = lines[0].strip().split()
            num_evids = int(pars[0])
            for i in range(num_evids):
                id = int(pars[2*i+1])
                state = int(pars[2*i+2])
                self.evids.append((id, state))

    def read_map(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        if len(lines) > 1:
            num_vars = int(lines[1])
            for i in range(num_vars):
                id = int(lines[i+2])
                self.query_var.append(id)
        else:
            pars = lines[0].strip().split()
            num_vars = int(pars[0])
            for i in range(num_vars):
                id = int(pars[i+1])
                self.query_var.append(id)

    def read_sdp(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        # decision
        id = int(lines[0].strip())
        self.dec.append((id, 1))

        # unobserved
        pars = lines[1].strip().split()
        num_unobserved = int(pars[0])
        for i in range(num_unobserved):
            id = int(pars[i+1])
            self.unobserved.append(id)

        # evidence
        pars = lines[2].strip().split()
        num_evid = int(pars[0])
        for i in range(num_evid):
            id = int(pars[2*i+1])
            state = int(pars[2*i+2])
            self.evids.append((id, state))

        # threshold
        self.dec_thr = float(lines[3].strip())

    def write(self, filename, evid_file='', query_file='', sdp_file=''):
        name, ext = os.path.splitext(filename)
        if len(evid_file) == 0:
            evid_file = filename + '.evid'
        if len(query_file) == 0:
            map_file = filename + '.map'
            query_file = filename + '.query'
        if len(sdp_file) == 0:
            sdp_file = filename + '.sdp'
            query_file = filename + '.query'

        if ext == '.uai':
            if self.kind == 'BN':
                self.write_uai_bn(filename)
            elif self.kind == 'ID':
                self.write_uai_id(filename)
        elif ext == '.limid':
            self.write_limid(filename)
        else:
            raise ValueError('Unknown extension:', ext)

        if self.query in evid_query:
            self.write_evidence(evid_file)

        if self.query in map_query:
            self.write_map_query(map_file)

        if self.query in sdp_query:
            self.write_sdp_query(sdp_file)

    def write_uai_bn(self, filename):
        f = open(filename, 'w')
        f.write('BAYES\n')
        f.write('%d\n' % self.num_nodes)
        for i, n in enumerate(self.nodes):
            f.write('%d' % n.num_states)
            if i + 1 < len(self.nodes):
                f.write(' ')
            else:
                f.write('\n')

        # edges
        f.write('%d\n' % self.num_nodes)
        for i, n in enumerate(self.nodes):
            f.write('%d ' % (len(n.parents)+1))
            for p in n.parents:
                f.write('%d ' % p.id)
            f.write('%d\n' % n.id)
        f.write('\n')

        # cpts
        for i, n in enumerate(self.nodes):
            num_val = len(n.cpt) * len(n.cpt[0])
            f.write('%d\n' % num_val)
            for row in n.cpt:
                f.write(' ')
                for k, val in enumerate(row):
                    f.write('%f' % val)
                    if k+1 < len(row):
                        f.write(' ')
                    else:
                        f.write('\n')
            f.write('\n')

    def write_limid(self, outfile):
        self.topo_sort()

        f = open(outfile, 'w')
        f.write('ID\n')

        # number of variables
        num_vars = 0
        uai_id = 0
        for n in self.nodes:
            if n.kind == 'chance' or n.kind == 'decision':
                num_vars += 1
                n.uai_id = uai_id
                uai_id += 1
        f.write('%d\n' % num_vars)

        # number of states
        for n in self.nodes:
            if n.kind == 'chance' or n.kind == 'decision':
                f.write('%d ' % n.num_states)
        f.write('\n')

        # type of nodes
        num_c = 0
        num_d = 0
        for n in self.nodes:
            if n.kind == 'chance':
                f.write('c ')
                num_c += 1
            elif n.kind == 'decision':
                f.write('d ')
                num_d += 1
        f.write('\n')

        # partial order
        written = []
        for n in self.nodes:
            if n.kind == 'decision':
                for p in n.parents:
                    if p.kind == 'chance' and p.uai_id not in written:
                        f.write('%d ' % (p.uai_id))
                        written.append(p.uai_id)
                f.write('%d ' % (n.uai_id))
        for n in self.nodes:
            if n.kind == 'chance' and n.uai_id not in written:
                f.write('%d ' % (n.uai_id))
        f.write('\n')

        # relations
        num_table = self.num_nodes + self.num_utils
        f.write('%d\n' % num_table)
        for n in self.nodes:
            if n.kind == 'decision':
                f.write('d ')
                f.write('%d ' % (1 + len(n.parents)))
                for p in n.parents:
                    f.write('%d ' % p.uai_id)
                f.write('%d ' % n.uai_id)
                f.write('\n')
        for r in self.nodes:
            if r.kind == 'chance':
                f.write('p ')
                f.write('%d ' % (1 + len(r.parents)))
                for n in r.parents:
                    f.write('%d ' % n.uai_id)
                f.write('%d ' % r.uai_id)
                f.write('\n')
        for r in self.utils:
            f.write('u ')
            f.write('%d ' % len(r.parents))
            for n in r.parents:
                f.write('%d ' % n.uai_id)
            f.write('\n')

        f.write('\n')
        # CPT
        for n in self.nodes:
            if n.kind == 'decision':
                f.write('0\n\n')

        for r in self.nodes:
            if r.kind == 'chance':
                f.write('%d\n' % (len(r.cpt)*len(r.cpt[0])))
                num_state = r.num_states
                num_row = len(r.cpt)
                for i in range(num_row):
                    for j in range(num_state):
                        f.write('%f ' % r.cpt[i][j])
                    f.write('\n')
                f.write('\n')

        for r in self.utils:
            f.write('%d\n' % len(r.vals))
            for v in r.vals:
                f.write('%f\n' % v)
            f.write('\n')

    def write_uai_id(self, filename):
        # head, tail = os.path.split(filename)
        name, ext = os.path.splitext(filename)
        assert (ext == '.uai')

        uai_file = name + '.uai'
        id_file = name + '.id'
        pvo_file = name + '.pvo'

        self.topo_sort()

        f = open(uai_file, 'w')
        f.write('ID\n')

        # number of variables
        num_vars = 0
        uai_id = 0
        for n in self.nodes:
            # if n.kind == 'chance' or n.kind == 'decision':
            num_vars += 1
            n.uai_id = uai_id
            uai_id += 1
        for n in self.utils:
            n.uai_id = uai_id
            uai_id += 1
        f.write('%d\n' % num_vars)

        # number of states
        for n in self.nodes:
            if n.kind == 'chance' or n.kind == 'decision':
                f.write('%d ' % n.num_states)
        f.write('\n')

        # type of nodes
        f_id = open(id_file, 'w')
        f_id.write('%d\n' % num_vars)
        num_c = 0
        num_d = 0
        for n in self.nodes:
            if n.kind == 'chance':
                f_id.write('C ')
                num_c += 1
            elif n.kind == 'decision':
                f_id.write('D ')
                num_d += 1
        f_id.write('\n')
        f_id.write('%d\n' % (num_c + self.num_utils))
        for n in self.nodes:
            if n.kind == 'chance':
                f_id.write('P ')
        for n in self.utils:
            f_id.write('U ')
        f_id.write('\n')
        f_id.close()

        f_pvo = open(pvo_file, 'w')
        f_pvo.write('%d;\n' % num_vars)
        # partial order
        unused_vars = list(range(self.num_nodes))
        level_vars = []
        for n in self.nodes:
            if n.kind == 'decision':
                unused_vars.remove(n.uai_id)
                vars = []
                for p in n.parents:
                    if p.kind == 'chance':
                        vars.append(p.uai_id)
                    try:
                        unused_vars.remove(p.uai_id)
                    except ValueError:
                        pass
                if len(vars) > 0:
                    level_vars.append(vars)
                level_vars.append([n.uai_id])
        if len(unused_vars) > 0:
            level_vars.append(unused_vars)
        # f.write('\n')
        f_pvo.write('%d;\n' % len(level_vars))
        for vars in level_vars[::-1]:
            for id in vars:
                f_pvo.write('%d ' % id)
            f_pvo.write(';\n')
        f_pvo.close()

        # relations
        num_table = num_c + self.num_utils
        f.write('%d\n' % num_table)
        # for n in self.nodes:
        #     if n.kind == 'decision':
        #         # f.write('d ')
        #         f.write('%d ' % (1 + len(n.parents)))
        #         for p in n.parents:
        #             f.write('%d ' % p.uai_id)
        #         f.write('%d ' % n.uai_id)
        #         f.write('\n')
        for r in self.nodes:
            if r.kind == 'chance':
                # f.write('p ')
                f.write('%d ' % (1 + len(r.parents)))
                for n in r.parents:
                    f.write('%d ' % n.uai_id)
                f.write('%d ' % r.uai_id)
                f.write('\n')
        for r in self.utils:
            # f.write('u ')
            f.write('%d ' % len(r.parents))
            for n in r.parents:
                f.write('%d ' % n.uai_id)
            f.write('\n')
        f.write('\n')
        # CPT
        # for n in self.nodes:
        #     if n.kind == 'decision':
        #         f.write('0\n\n')

        for r in self.nodes:
            if r.kind == 'chance':
                f.write('%d\n' % (len(r.cpt)*len(r.cpt[0])))
                num_state = r.num_states
                num_row = len(r.cpt)
                for i in range(num_row):
                    for j in range(num_state):
                        f.write('%f\n' % r.cpt[i][j])
                    # f.write('\n')
                f.write('\n')

        for r in self.utils:
            f.write('%d\n' % len(r.vals))
            for v in r.vals:
                f.write('%f\n' % v)
            f.write('\n')

    def write_evidence(self, outfile, type='single_line'):
        f = open(outfile, 'w')

        if type == 'multiple_line':
            f.write('/* Evidence */\n')
            f.write('%d\n' % len(self.evids))
            for (id, state) in self.evids:
                f.write('%d %d\n' % (id, state))
        elif type == 'single_line':
            f.write('%d' % len(self.evids))
            for (id, state) in self.evids:
                f.write(' %d %d' % (id, state))
            f.write('\n')

    def write_map_query(self, outfile, type='single_line'):
        f = open(outfile, 'w')

        if type == 'multiple_line':
            f.write('# map query file\n')
            f.write('%d\n' % (len(self.query_var)))
            for i in self.query_var:
                f.write('%d\n' % i)
        elif type == 'single_line':
            f.write('%d' % (len(self.query_var)))
            for i in self.query_var:
                f.write(' %d' % i)
            f.write('\n')

    def write_sdp_query(self, outfile):
        f = open(outfile, 'w')

        f.write('%d\n' % (self.dec[0][0]))

        f.write('%d ' % len(self.unobserved))
        for i in self.unobserved:
            f.write('%d ' % i)
        f.write('\n')

        f.write('%d ' % len(self.evids))
        for (i, n) in self.evids:
            f.write('%d %d ' % (i, n))
        f.write('\n')

        f.write('%f\n' % self.dec_thr)

    def dfs(self, reverse=False):
        for n in self.nodes:
            n.visit = False

        if not reverse:
            for n in self.nodes:
                if len(n.parents) == 0:
                    n.visit = True
                    self.dfs_rec(n)
        else:
            for n in self.nodes:
                if len(n.children) == 0:
                    n.visit = True
                    self.dfs_rec(n, reverse)

    def dfs_rec(self, n, reverse=False):
        if not reverse:
            for c in n.children:
                if c.visit == False:
                    c.visit = True
                    self.dfs_rec(c)
        else:
            for p in n.parents:
                if p.visit == False:
                    p.visit = True
                    self.dfs_rec(p, reverse)

        self.finish_id += 1
        n.finish_id = self.finish_id

    def topo_sort(self, method=0):
        '''
        method  0: dfs
                1: reverse dfs
                2: recursive remove parent
        '''
        if method == 0:
            self.dfs()
            self.nodes.sort(reverse=True, key=lambda n: n.finish_id)
        elif method == 1:
            self.dfs(reverse=True)
            self.nodes.sort(reverse=False, key=lambda n: n.finish_id)
        elif method == 2:
            order = self.rec_remove()
            self.nodes = [self.id2node[id] for id in order]

    def rec_remove(self):
        # copy nodes
        gnodes = []
        id2gnodes = {}
        for n in self.nodes:
            if n.depend:
                gn = gNode(n)
                gnodes.append(gn)
                id2gnodes[gn.id] = gn

        order = []
        while len(gnodes) > 0:
            # find no parent
            choice = None
            for gn in gnodes:
                if len(gn.parents) == 0:
                    choice = gn
                    break
            # remove
            for id in choice.children:
                id2gnodes[id].parents.remove(choice.id)
            order.append(choice.id)
            gnodes.remove(choice)
        return order

    def normalize_util(self):
        total_u_shift = 0
        max_u_scale = -math.inf
        for u in self.utils:
            u_max = max(u.vals)
            u_min = min(u.vals)

            total_u_shift -= u_min
            u.vals = [(val - u_min) for val in u.vals]

            u_scale = u_max - u_min
            max_u_scale = max(u_scale, max_u_scale)

        for u in self.utils:
            u.vals = [(val / max_u_scale) for val in u.vals]

        return max_u_scale, total_u_shift

    def create_super_util(self):
        id = self.num_nodes + 1
        self.super_util = Node(id, 'utility')
        self.nodes.append(self.super_util)
        self.id2node[id] = self.super_util

        for u in self.utils:
            self.super_util = self.merge_util(self.super_util, u)

        for p in self.super_util.parents:
            p.children.append(self.super_util)

    # merge u2 into u1

    def merge_util(self, u1, u2):
        if u1 == None or u2 == None:
            raise ValueError('Util node cannot be None')

        # just return if u2 is empty
        if len(u2.vals) == 0 and len(u2.parents) == 0:
            return u1

        # just copy if u1 is empty
        if len(u1.vals) == 0 and len(u1.parents) == 0:
            u1.vals = u2.vals
            u1.parents = u2.parents
            return u1

        comb1 = self.parent_comb(u1)
        comb2 = self.parent_comb(u2)
        assert (len(comb1) == len(u1.vals)), (len(comb1), len(u1.vals))
        assert (len(comb2) == len(u2.vals)), (len(comb2), len(u2.vals))

        # find the same parent nodes
        pair = []
        for i, p2 in enumerate(u2.parents):
            if p2 in u1.parents:
                j = u1.parents.index(p2)
                pair.append((j, i))
            else:
                u1.parents.append(p2)

        # Cartesian product of utility values
        values = []
        for i, c1 in enumerate(comb1):
            for j, c2 in enumerate(comb2):
                # check if different states of the same node
                conflict = False
                for (ip, jp) in pair:
                    if c1[ip] != c2[jp]:
                        conflict = True
                        break
                if conflict:
                    continue

                # add up utilities
                val1 = u1.vals[i]
                val2 = u2.vals[j]
                values.append(val1 + val2)

        u1.vals = values
        comb = self.parent_comb(u1)
        assert (len(comb) == len(u1.vals)), (len(comb), len(u1.vals))

        return u1

    def parent_comb(self, n):
        args = []
        for p in n.parents:
            args.append(p.states)
        comb = itertools.product(*args)

        comb = [c for c in comb]
        if len(comb) == 1 and comb[0] == ():
            return []
        return comb

    def assign_dec_level(self):
        # assume the nodes are in topological order
        for n in self.nodes[::-1]:
            for c in n.children:
                if n.kind == 'chance' or (n.kind == 'decision' and c.kind == 'chance'):
                    n.dec_level = max(n.dec_level, c.dec_level)
            if n.kind == 'decision':
                n.dec_level += 1
                self.max_dec_level = max(self.max_dec_level, n.dec_level)

                nodes = self.level2dec.get(n.dec_level)
                if nodes is None:
                    self.level2dec[n.dec_level] = [n]
                else:
                    nodes.append(n)

    def bn2id(self, num_dec, num_util, num_parents):
        ids = random.sample(range(self.num_nodes), num_dec)
        for id in ids:
            self.nodes[id].kind = 'decision'

        for u in range(num_util):
            self.num_utils += 1
            id = self.num_nodes + self.num_utils + 1
            n = Node(id, 'utility')
            self.utils.append(n)
            self.id2util[id] = n
            ids = random.sample(range(self.num_nodes), num_parents)
            num_vals = 1
            for id in ids:
                p = self.id2node[id]
                n.parents.append(p)
                num_vals *= p.num_states

            for i in range(num_vals):
                n.vals.append(random.choice(range(10)))

    def gen_evid(self, num_evid):
        chance_id = []
        for i, n in enumerate(self.nodes):
            if n.kind == 'chance':
                chance_id.append(i)
        if num_evid >= len(chance_id):
            num_evid = len(chance_id) // 2

        ids = random.sample(range(len(chance_id)), num_evid)
        for i in ids:
            n = self.nodes[chance_id[i]]
            evid = random.choice(range(n.num_states))
            self.evids.append((n.id, evid))

    def gen_map(self, num_cared, num_evids):
        # exclude origin evidences
        node_ids = list(range(self.num_nodes))
        for (id, state) in self.evids:
            n = self.id2node[id]
            i = self.nodes.index(n)
            node_ids.remove(i)

        ids = random.sample(node_ids, num_cared + num_evids)
        # cared vars
        self.query_var = ids[:num_cared]

        # evidence
        # self.evids = []
        for i in ids[num_cared:num_cared + num_evids]:
            n = self.nodes[i]
            evid = random.choice(range(n.num_states))
            self.evids.append((n.id, evid))

    def gen_sdp(self, num_dec, num_unobserved, num_evidence):
        if num_dec != 1:
            num_dec = 1  # only 1 decision now
            print('Number of decision can only be 1')

        for i in range(500):
            ids = random.sample(range(self.num_nodes), num_dec+num_unobserved+num_evidence)
            if self.nodes[0].num_states == 2:
                break

        if self.nodes[0].num_states != 2:
            print('Cannot find binary decision node')

        # decision
        n = self.nodes[0]
        self.dec = [(n.id, 1)]
        # for i in ids[:num_dec]:
        #     n = self.nodes[i]
        #     dec = random.choice(range(n.num_states))
        #     self.dec.append((n.id, dec))

        # unobserved
        self.unobserved = ids[num_dec:num_dec+num_unobserved]

        # evidence
        self.evids = []
        for i in ids[num_dec+num_unobserved:num_dec+num_unobserved+num_evidence]:
            n = self.nodes[i]
            evid = random.choice(range(n.num_states))
            # evid = 1
            self.evids.append((n.id, evid))

    def construct_causal_graph(self):
        for (id, state) in self.evids:
            n = self.nodes[id]

            # remove edge
            for p in n.parents:
                p.children.remove(n)
            n.parents = []

            # set value
            n.cpt = [[0 for i in range(n.num_states)]]
            n.cpt[0][state] = 1

    def cal_num_entry(self):
        entry = 0
        for n in self.nodes:
            if n.depend:
                if n.kind == 'chance':
                    entry += len(n.cpt) * len(n.cpt[0])

        return entry

    def mark_redundent(self, enable_d=False):
        cared = []
        if self.kind == 'BN':
            cared = [id for (id, state) in self.evids] + \
                self.query_var + self.unobserved

            if enable_d:
                cared += [id for (id, state) in self.dec]

            if len(cared) == 0:
                return

            for n in self.nodes:
                n.depend = False

            for id in cared:
                self.mark_depend(self.id2node[id])

        elif self.kind == 'ID':
            for n in self.nodes:
                n.depend = False

            for n in self.utils:
                for p in n.parents:
                    self.mark_depend(p)

        if not enable_d:
            self.copy_not_depend_d()

    def mark_depend(self, n):
        if n.depend:
            return
        n.depend = True
        for p in n.parents:
            self.mark_depend(p)

    def copy_not_depend_d(self):
        for n in self.nodes:
            n.not_depend_d = not n.depend

    def count_depend(self):
        num = 0
        for n in self.nodes:
            if n.depend:
                num += 1

        return num

    def minfill(self):
        # copy nodes
        gnodes = []
        id2gnodes = {}
        for n in self.nodes:
            if n.depend:
                gn = gNode(n)
                gnodes.append(gn)
                id2gnodes[gn.id] = gn

        # start eliminate
        minfill_order = []
        while len(gnodes) > 0:
            # find minfill
            min_num = math.inf
            choice = None
            for gn in gnodes:
                num = self.cal_fill(id2gnodes, gn)
                if num < min_num:
                    choice = gn
                    min_num = num
            gnodes = self.do_fill(gnodes, id2gnodes, choice)
            minfill_order.append(choice.id)

        self.minfill_order = minfill_order
        self.copy_nodes = self.nodes.copy()
        self.nodes = [self.id2node[id] for id in minfill_order]

    def cal_fill(self, id2gnodes, gn, weighted=True):
        num = 0
        for id in gn.neighbors:
            neigh = id2gnodes[id]
            added_neigh = (set(gn.neighbors) | set(neigh.neighbors)) - set(neigh.neighbors)
            if not weighted:
                num += len(added_neigh)
            else:
                for nid in added_neigh:
                    num += self.id2node[id].num_states * self.id2node[nid].num_states
        return num

    def do_fill(self, gnodes, id2gnodes, gn):
        gnodes.remove(gn)
        for id in gn.neighbors:
            neigh = id2gnodes[id]
            neigh.neighbors.remove(gn.id)
            neigh.neighbors = list(set(gn.neighbors) | set(neigh.neighbors))
            neigh.neighbors.remove(id)

        return gnodes

    def find_connected_components(self):
        for n in self.nodes:
            n.visit = False

        num_components = 0
        for n in self.nodes:
            if not n.depend:
                continue
            if n.visit:
                continue
            self.dfs_cc(n, num_components)
            num_components += 1

        return num_components

    def dfs_cc(self, n, component_label):
        '''
        to find connected components (undirected graph)
        '''

        n.visit = True
        n.component_label = component_label
        stack = [n]
        cnt = 0
        while len(stack) > 0:
            cnt += 1
            node = stack.pop()
            for c in (node.parents + node.children):
                if not c.depend:
                    continue
                if c.visit:
                    continue
                c.visit = True
                c.component_label = component_label
                if c in stack:
                    print('already in')
                    import pdb
                    pdb.set_trace()
                stack.append(c)

    def collect_cared_nodes(self):
        self.copy_nodes = self.nodes.copy()

        # cared components
        if self.query == 'SDP':
            cared_id = self.dec[0][0]
            cared_component_label = self.id2node[cared_id].component_label
            for n in self.nodes:
                n.cared = False
        else:
            return

        self.nodes = [n for n in self.nodes if (
            n.depend and n.component_label == cared_component_label)]

        for n in self.nodes:
            n.cared = True

    def relabel_nodes(self):
        self.num_nodes = len(self.nodes)
        # node id
        for i, n in enumerate(self.nodes):
            n.id = i

        # evidence
        new_evids = []
        for (id, state) in self.evids:
            n = self.id2node[id]
            if n in self.nodes:
                new_id = n.id
            else:
                continue
            new_evids.append((new_id, state))
        self.evids = new_evids

        # map
        new_query_var = []
        for id in self.query_var:
            n = self.id2node[id]
            if n in self.nodes:
                new_id = n.id
            else:
                continue
            new_query_var.append(new_id)
        self.query_var = new_query_var

        # decision
        if self.query == 'SDP':
            id, state = self.dec[0]
            new_id = self.id2node[id].id
            self.dec[0] = (new_id, state)

        # unobserved
        new_unobserved = []
        for id in self.unobserved:
            n = self.id2node[id]
            if n in self.nodes:
                new_id = n.id
            else:
                continue
            new_unobserved.append(new_id)
        self.unobserved = new_unobserved
