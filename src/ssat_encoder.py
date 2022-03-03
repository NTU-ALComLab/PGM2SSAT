import itertools
import math
import os
import datetime

from quine_mccluskey.qm import QuineMcCluskey


class SSATEncoder:
    def __init__(self, net, encode, query, num_bit=20, log_state=False, prune=False, connected_component=False, opt='esp', share_val=False):
        '''
        net(Network): the Network object 
        encode(string): the encoding method 
        query(string): the query of this encoding
        num_bit(int): number of bits to share the values
        log_state(bool): whether use log(state) to encode states
        prune(bool): whether apply network pruning
        opt(str): use quine-mccluskey or espresso minimization
        share_val(bool): whether share value across table
        '''

        # network to encode
        self.net = net
        self.causal = net.causal
        self.prune = prune if query in ['PE', 'SDP', 'MEU'] else False
        self.cc = connected_component

        self.encode = encode
        self.query = query
        self.opt = opt

        self.super_util = False

        # the error tolerance
        self.digit = 16
        self.min_val = 10**(-self.digit)

        # flag of using conditional probability SSAT
        self.use_cp = False

        # bit sharing when encoding cpt
        self.num_bit = num_bit
        self.num_shared_cpt = 0
        self.thr_cpt_size = 255
        self.thr_shared_num = 1

        # share varaibles between tables
        self.share_val = share_val
        self.node_id2var_pool = {}
        self.node_id2merge_list = {}
        self.node_id2vars = {}

        self.log_state = log_state      # encoding method of state vars
        self.encode_state_order = 1     # 0: from 00 to 11; 1: from 11 to 00

        self.var_id = 0
        self.node_id2state_vars = {}   # mappings if self.log_state = False
        self.node_id2state_cls = {}    # mappings if self.log_state = True
        self.node_id2state_cls_full = {}

        # threshold varaible for SDP
        self.thr_var = 0

        # the introduced existential variables for the last level
        self.intro_vars = []

        # chance nodes
        self.state_vars = []
        self.rand_vars = []
        # decision nodes
        self.dec_vars = []
        self.ob_vars = []
        self.node_id2dec_vars = {}
        self.node_id2ob_vars = {}
        # utiliy nodes
        self.util_state_vars = []
        self.util_id2state_cls = {}
        self.util_vars = []

        # the clauses encoding each node
        self.node_id2clauses = {}
        self.clauses = []

        # scale of variables
        self.scale = 1

        # meu calculation for Cartesian product utility nodes
        self.max_util = 1
        self.min_util = 0

        # meu calculation for linear encoding utility nodes
        self.u_scale = 1
        self.u_shift = 0

        # summary
        self.pool_num = []

        # for causal graph
        self.node_id2edge_var = {}  # the variable controlling nodes' edge to parents

    # reset all vars and clauses

    def reset(self):
        self.node_id2var_pool = {}
        self.node_id2merge_list = {}
        self.node_id2vars = {}

        self.var_id = 0
        self.node_id2state_vars = {}   # mappings if self.log_state = False
        self.node_id2state_cls = {}    # mappings if self.log_state = True
        self.node_id2state_cls_full = {}

        # the introduced existential variables for the last level
        self.intro_vars = []

        # chance nodes
        self.state_vars = []
        self.rand_vars = []
        # decision nodes
        self.dec_vars = []
        self.ob_vars = []
        self.node_id2dec_vars = {}
        self.node_id2ob_vars = {}
        # utiliy nodes
        self.util_vars = []

        self.clauses = []

        # meu calculation
        self.scale = 1
        self.max_util = 1
        self.min_util = 0

        # summary
        self.pool_num = []

        # for causal graph
        self.node_id2edge_var = {}  # the variable controlling nodes' edge to parents

    # network to SSAT

    def tossat(self):
        print('Total number of nodes = ', self.net.num_nodes)
        if self.prune:
            self.net.mark_redundent()
            print('Pruned number of nodes = ', self.net.count_depend())
            if self.query == 'SDP':
                self.net.mark_redundent(enable_d=True)
                print('Pruned (with d) number of nodes = ', self.net.count_depend())
            self.net.nodes = [n for n in self.net.nodes if n.depend]

        entry = self.net.cal_num_entry()
        print('Total entry = ', entry)

        # print('Number of bit =', self.num_bit)
        self.net.topo_sort(method=0)

        if self.cc:
            num_components = self.net.find_connected_components()
            print('Number of connected components = ', num_components)
            self.net.collect_cared_nodes()

        # threshold variable for SDP
        if self.query == 'SDP':
            self.var_id += 1
            self.thr_var = self.var_id

        if self.net.kind == 'ID':
            if self.super_util:
                self.net.create_super_util()
            else:
                self.u_scale, self.u_shift = self.net.normalize_util()
            self.net.assign_dec_level()

        # encode states first
        for n in self.net.nodes:
            if not n.depend:
                continue

            if n.kind == 'chance':
                # edge variable
                if self.causal:
                    self.var_id += 1
                    self.node_id2edge_var[n.id] = self.var_id
                    self.intro_vars.append(self.var_id)
                self.encode_states(n)
            elif n.kind == 'decision':
                self.encode_states(n, dec=True)
            elif n.kind == 'utility':
                continue
            else:
                raise ValueError('Wrong kind of node', n.kind)

        if self.net.kind == 'ID' and not self.super_util:
            self.encode_util_mutual()

        # encode probabilities
        for n in self.net.nodes:
            if not n.depend:
                continue

            if n.kind == 'chance':
                self.encode_cpt(n)
            elif n.kind == 'decision':
                self.encode_observe(n)
            else:
                raise ValueError('Wrong kind of node', n.kind)

        if self.net.kind == 'ID':
            for n in self.net.utils:
                if self.super_util:
                    self.encode_super_util(n)
                else:
                    self.encode_util_val(n)

        self.encode_evid()

        if self.query == 'SDP':
            self.encode_sdp()

        self.print_summary()

        # self.net.minfill()
        # for n in self.net.nodes:
        #     if n.depend:
        #         print(n.id, [c.id for c in n.parents if c.depend], self.node_id2state_vars[n.id])
        self.net.nodes = self.net.nodes[::-1]

    def print_summary(self):
        print('-------Summary-------')
        print('Decision level:', self.net.max_dec_level)
        print('Scale =', self.scale)
        if self.super_util:
            print('Util value = (%f,%f)' % (self.max_util, self.min_util))
        else:
            print('Util scale = %f, Util shift = %f' % (self.u_scale, self.u_shift))
        if len(self.pool_num) > 0:
            print('Max number of prob = ', max(self.pool_num))
        print('Number of bit-shared cpt = ', self.num_shared_cpt)
        print('---------------------')

    def encode_chance_node(self, n):
        # edge variable
        if self.causal:
            self.var_id += 1
            self.node_id2edge_var[n.id] = self.var_id
            self.intro_vars.append(self.var_id)
        self.encode_states(n)
        self.encode_cpt(n)

    def encode_dec_node(self, n):
        self.encode_states(n, dec=True)
        self.encode_observe(n)

    def encode_util_node(self, n):
        self.encode_util_val(n)
        # self.encode_util_bit(n)

    def encode_util_mutual(self):
        num_vars = math.ceil(math.log(self.net.num_utils, 2))
        args = []
        # generate vars
        for i in range(num_vars):
            self.var_id += 1
            v = self.var_id
            self.util_state_vars.append(v)
            args.append([-v, v])

        # combination of vars as a state
        comb = itertools.product(*args)
        state_cls = [list(c) for c in comb]
        for i, u in enumerate(self.net.utils):
            self.util_id2state_cls[u.id] = state_cls[i]

        # redundant clauses
        redundant = []
        for cl in state_cls[self.net.num_utils:]:
            redundant.append(cl)
        merged = self.merge_state_cls(redundant)
        self.clauses += merged

    def encode_evid(self):
        evid_id = []
        for (node_id, state) in self.net.evids:
            if not self.net.id2node[node_id].cared:
                continue
            if not self.log_state:
                s = [self.node_id2state_vars[node_id][state]]
                self.clauses.append(s)
            else:
                s = self.node_id2state_cls[node_id][state]
                for v in s:
                    self.clauses.append([v])
            evid_id.append(node_id)

        # enable/disable the edge
        if self.causal:
            for n in self.net.nodes:
                if n.kind != 'chance':
                    continue
                if n.id in evid_id:
                    self.clauses.append([-self.node_id2edge_var[n.id]])
                else:
                    self.clauses.append([self.node_id2edge_var[n.id]])

    def encode_sdp(self):
        # decision
        for (id, state) in self.net.dec:
            if not self.log_state:
                s = [self.node_id2state_vars[id][state]]
                self.clauses.append(self.implication([self.thr_var], s))
            else:
                s = self.node_id2state_cls[id][state]
                for v in s:
                    self.clauses.append(self.implication([self.thr_var], [v]))

        # self.var_id += 1
        # self.clauses.append(self.implication([-self.thr_var], [self.var_id]))
        # self.rand_vars.append((self.var_id, self.net.dec_thr))

        # evidence are already encoded

    def encode_states(self, n, dec=False):
        '''
        n: node
        dec: is decision node?
        log_state: use log(|s|) vars to encode the states
        '''
        if not self.log_state:
            if n.num_states == 2:
                self.var_id += 1
                v = self.var_id
                if dec is True:
                    self.dec_vars.append(v)
                    self.node_id2dec_vars[n.id] = [v]
                    self.node_id2state_vars[n.id] = [-v, v]
                else:
                    self.state_vars.append(v)
                    self.node_id2state_vars[n.id] = [-v, v]
            else:
                vars = []
                for s in n.states:
                    self.var_id += 1
                    v = self.var_id
                    if dec is True:
                        self.dec_vars.append(v)
                    else:
                        self.state_vars.append(v)
                    vars.append(v)
                if dec is True:
                    self.node_id2dec_vars[n.id] = vars
                    self.node_id2state_vars[n.id] = vars
                else:
                    self.node_id2state_vars[n.id] = vars

                # mutual exclusion
                cl = []
                for i in range(len(vars)):
                    v1 = vars[i]
                    cl.append(v1)
                    for j in range(i+1, len(vars)):
                        v2 = vars[j]
                        self.clauses.append([-v1, -v2])
                self.clauses.append(cl)
        # use log(|s|) vars to encode states
        else:
            num_vars = math.ceil(math.log(n.num_states, 2))
            vars = []
            args = []
            # generate vars
            for i in range(num_vars):
                self.var_id += 1
                v = self.var_id
                if dec is True:
                    self.dec_vars.append(v)
                else:
                    self.state_vars.append(v)
                vars.append(v)
                args.append([-v, v])

            if dec is True:
                self.node_id2dec_vars[n.id] = vars
                self.node_id2state_vars[n.id] = vars
            else:
                self.node_id2state_vars[n.id] = vars

            # combination of vars as a state
            comb = itertools.product(*args)
            state_cls = [list(c) for c in comb]
            if self.encode_state_order == 1:
                state_cls = state_cls[::-1]
            self.node_id2state_cls[n.id] = state_cls[:n.num_states]
            self.node_id2state_cls_full[n.id] = state_cls
            # redundant states
            redundant = []
            for cl in state_cls[n.num_states:]:
                redundant.append(self.implication(cl, False))
            merged = self.merge_state_cls(redundant)
            if self.causal and n.kind == 'chance':
                e = self.node_id2edge_var[n.id]
                for cl in merged:
                    self.clauses.append([-e] + cl)
            else:
                self.clauses += merged

    def encode_cpt(self, n):
        '''
        Use a threshold to choose
        '''
        num_vars = len(n.cpt) * (n.num_states)
        if self.encode == 'bklm16':
            self.encode_cpt_bklm16(n)
        elif self.encode == 'sbk05':
            self.encode_cpt_row_mut_ex(n)
        elif self.encode == 'val':
            # self.encode_cpt_val(n)
            self.encode_cpt_clear(n)
        elif self.encode == 'all05':
            self.encode_cpt_bit05_old(n, split_cls=True)
            self.num_shared_cpt += 1
        else:   # bit sharing
            if len(n.cpt[0])*len(n.cpt) <= self.thr_cpt_size:
                self.encode_cpt_clear(n)
            else:
                self.num_shared_cpt += 1
                if self.encode == 'share_bit':
                    self.encode_cpt_clear(n, 'bit_share')
                    # self.encode_cpt_bit_log_sel(n, split_cls=True)
                    # self.encode_cpt_bit_sub(n, split_cls=True)
                elif self.encode == 'direct_bit':
                    self.encode_cpt_bit_sel(n, share_var=False)
                    # self.encode_cpt_bit_sel(n, share_var=True)
                elif self.encode == 'bit_sop':
                    self.encode_cpt_bit_function(n, single_po=True, rep='sop')
                elif self.encode == 'bit_aig':
                    self.encode_cpt_bit_function(n, single_po=False, rep='aig')
                else:
                    raise ValueError('Unknown encode method:', self.encode)

    def encode_cpt_clear(self, n, method='bklm16'):
        '''
        method: bklm16, bit_share
        '''
        merge_list = self.cpt2merge_list(n)
        parent_vars, node_vars = self.get_combination_vars(n)
        vars = parent_vars + node_vars
        sel_var = None
        if method == 'bit_share':
            # import pdb
            # pdb.set_trace()
            merge_list, onset_merge_list, offset_merge_list = self.bit_share_merge_list(merge_list)
            onset_merge_list = self.simplify_merge_list(onset_merge_list)
            offset_merge_list = self.simplify_merge_list(offset_merge_list)
            self.encode_bit_merge_list(
                n, onset_merge_list, offset_merge_list, vars, imply_rand=True)
        merge_list = self.simplify_merge_list(merge_list)
        var_pool = self.encode_merge_list(n, merge_list, vars, sel_var=sel_var)

        if self.share_val:
            self.node_id2merge_list[n.id] = merge_list
            self.node_id2var_pool[n.id] = var_pool
            self.node_id2vars[n.id] = vars

    def encode_cpt_bklm16(self, n):
        '''
        reimplement bklm16
        '''
        merge_lists = self.cpt2merge_list(n, seperate_state=True)
        parent_vars, node_vars = self.get_combination_vars(n)
        vars = parent_vars + node_vars

        new_merge_list = {}
        for merge_list in merge_lists:
            res = self.simplify_merge_list(merge_list)
            for prob, pats in res.items():
                new_pats = new_merge_list.get(round(prob, self.digit))
                if new_pats is None:
                    new_merge_list[round(prob, self.digit)] = pats
                else:
                    new_pats += pats

        self.encode_merge_list(n, new_merge_list, vars, share_neg=False)

    # encode each prob value as a variable

    def encode_cpt_val(self, n, split_cls=False):
        '''
        origin:
        alpha & s1 -> r1
        alpha & s2 -> r2
        alpha & s3 -> r3
        '''
        vars = self.node_id2state_vars[n.id]
        if self.log_state:
            state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        # to have variable sharing
        var_pool = {}
        # conditional probability
        for j, comb in enumerate(combs):
            p = 1
            base_cl = []
            if self.causal:
                base_cl = [-self.node_id2edge_var[n.id]]
            base_cl += [-v for v in comb]
            if split_cls:
                self.var_id += 1
                id = self.var_id
                self.intro_vars.append(id)
                self.clauses.append(base_cl + [id])
                base_cl = [-id]
            # encode each value in a row
            false_cls = []
            for i in range(n.num_states):
                prob = n.cpt[j][i]

                # the assignment of this state
                if not self.log_state:
                    s = [vars[i]]
                else:
                    s = state_cls[i]

                if prob >= 1-self.min_val/2:
                    false_cls = []
                    for v in s:
                        self.clauses.append(base_cl + [v])
                    break
                elif prob <= self.min_val/2:
                    # self.clauses.append(base_cl + self.implication(s, False))
                    false_cls.append(self.implication(s, False))
                else:
                    # find variables with same/complement probability to share
                    va = var_pool.get(round(prob, self.digit))
                    if va is None:
                        va = var_pool.get(round(1-prob, self.digit))
                        if va is not None:
                            va = -va
                    if va is None:
                        self.var_id += 1
                        id = self.var_id
                        self.rand_vars.append((id, prob))
                        var_pool[round(prob, self.digit)] = id
                        va = id
                    self.clauses.append(base_cl + self.implication(s, [va]))
            merged = self.merge_state_cls(false_cls)
            for cl in merged:
                self.clauses.append(base_cl + cl)
        # print('Pool = ', var_pool)
        self.pool_num.append(len(var_pool.keys()))

    def encode_cpt_row_mut_ex(self, n, split_cls=False, imply_rand=False, imply_merge=False):
        # mutual exclusion of randomized variables
        '''
        origin:
            alpha -> (x1 <- r1)
            alpha -> (x2 <- r1' & r2)
            alpha -> (x3 <- r1' & r2')
        split_cls:
            alpha -> z
            z -> (x1 <- r1)
                ...
        imply_rand:
            alpha -> (x1 -> r1)
            alpha -> (x2 -> r1' & r2)
            alpha -> (x3 -> r1' & r2')
            the above clause in CNF:
            alpha -> (x1 -> r1)
            alpha -> (x2 -> r1')
            alpha -> (x2 -> r2)
            alpha -> (x3 -> r1')
            alpha -> (x3 -> r2')
        imply_merge: todo
        '''

        vars = self.node_id2state_vars[n.id]
        if self.log_state:
            state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        # to have variable sharing
        var_pool = [{} for k in range(n.num_states-1)]

        # conditional probability
        for j, comb in enumerate(combs):
            p = 1
            base_cl = []
            if self.causal:
                base_cl = [-self.node_id2edge_var[n.id]]
            base_cl += [-v for v in comb]
            if split_cls:
                self.var_id += 1
                id = self.var_id
                self.intro_vars.append(id)
                self.clauses.append(base_cl + [id])
                base_cl = [-id]

            randv2clsid = {}    # map random var to its clause id, used in ipmly_merge
            prob_cl = []
            for i in range(n.num_states):
                val = n.cpt[j][i]
                # the assignment of this state
                if not self.log_state:
                    s = [vars[i]]
                else:
                    s = state_cls[i]

                # n-1 random variables for probability distribution
                if i != n.num_states-1:
                    if p > self.min_val/2:
                        prob = val / p  # normalize probability
                        p -= val
                    else:
                        prob = 0

                    # prob = 1
                    if prob >= 1-self.min_val/2:
                        if not imply_rand:
                            for v in s:
                                self.clauses.append(base_cl + prob_cl + [v])
                        else:
                            for r in prob_cl:
                                self.clauses.append(base_cl + [-v] + [-r])
                            # self.clauses.append(base_cl + [-v])
                    # prob = 0
                    elif prob <= self.min_val/2:
                        # self.clauses.append(base_cl + prob_cl + [-v])
                        if imply_rand:
                            # for r in prob_cl:
                            #     self.clauses.append(base_cl + [-v] + [-r])
                            self.clauses.append(base_cl + [-v])
                        # pass
                    # 0 < prob < 1
                    else:
                        # find variables to share
                        va = var_pool[i].get(prob)
                        # va = None
                        if va is None:
                            self.var_id += 1
                            id = self.var_id
                            self.rand_vars.append((id, prob))
                            var_pool[i][prob] = id
                            va = id

                        if not imply_rand:
                            for v in s:
                                self.clauses.append(
                                    base_cl + prob_cl + [-va] + [v])
                        else:
                            if not imply_merge:
                                for r in prob_cl:
                                    self.clauses.append(base_cl + [-v] + [-r])
                                self.clauses.append(base_cl + [-v] + [va])
                            # else:
                            #     for r in prob_cl:
                            #         cls_id = randv2clsid.get(r)
                            #         if cls_id is None:
                            #             randv2clsid[r] = len(self.clauses)
                            #             self.clauses.append(base_cl + [-r] + [-v])
                            #         else:
                            #             self.clauses[cls_id] += [-v]
                            #     self.clauses.append(base_cl + [va] + [-v])

                        prob_cl.append(va)

                else:
                    if p <= self.min_val/2:
                        if imply_rand:
                            # for r in prob_cl:
                            self.clauses.append(base_cl + [-v])
                            # pass
                    elif p >= 1 - self.min_val/2:
                        if not imply_rand:
                            for v in s:
                                self.clauses.append(base_cl + prob_cl + [v])
                        else:
                            for r in prob_cl:
                                self.clauses.append(base_cl + [-v] + [-r])
                    else:
                        if not imply_rand:
                            for v in s:
                                self.clauses.append(base_cl + prob_cl + [v])
                        else:
                            if not imply_merge:
                                for r in prob_cl:
                                    self.clauses.append(base_cl + [-v] + [-r])
                            # else:
                            #     for r in prob_cl:
                            #         cls_id = randv2clsid.get(r)
                            #         if cls_id is None:
                            #             # randv2clsid[r] = len(self.clauses)
                            #             self.clauses.append(base_cl + [-r] + [-v])
                            #         else:
                            #             self.clauses[cls_id] += [-v]

    def encode_cpt_bit_function(self, n, single_po=True, rep='sop'):
        '''
        n: node
        single_po: flag to separate po when using sop
        rep: sop/aig
        '''
        assert (self.log_state is True)
        if rep == 'aig':
            assert (single_po is False)
            opt_cmd = ''
            # opt_cmd = 'if -K 6 -m; mfs2 -W 100 -F 100 -D 100 -L 100 -C 1000000; compress2rs;'
            opt_cmd = 'dc2;'*3

        state_cls = self.node_id2state_cls[n.id]

        input_vars = []
        for p in n.parents:
            input_vars += self.node_id2state_vars[p.id]
        input_vars += self.node_id2state_vars[n.id]
        num_input = len(input_vars)

        num_bit = self.find_max_bit(n)

        bit_vars = self.add_bit_vars(num_bit)
        num_sel, sel_vars, sel_combs = self.add_select_vars(num_bit)
        # new_bit_vars = self.map_bit_sel(bit_vars, sel_combs)

        p1_onset, onset, offset = self.cpt2minterm(n, num_bit, num_sel, sel_combs)
        # all zeros
        if len(p1_onset) == 0 and len(onset) == 0:
            self.var_id += 1
            v = self.var_id
            self.clauses.append([v])
            self.clauses.append([-v])
            return
        # all ones
        if len(offset) == 0:
            return

        if rep == 'sop':
            # onset
            if single_po:
                for i, b in enumerate(bit_vars):
                    out_id = num_bit - i
                    single_onset = []
                    for pat in onset:
                        if pat[-out_id] == '1':
                            single_onset.append(pat[:-num_bit] + '1')
                    if len(single_onset) == 0:
                        continue

                    self.write_pla(num_input, 1, single_onset,
                                   'pla/on%d.pla' % (i))
                    cmd = './espresso pla/on%d.pla > pla/out_on%d.pla' % (i, i)
                    # cmd = 'cp pla/on%d.pla pla/out_on%d.pla' % (i, i)
                    os.system(cmd)
                    opt_onset = self.read_pla('pla/out_on%d.pla' % (i))
                    for pat in opt_onset:
                        self.pattern2onset_clause(pat, input_vars, [sel_combs[i]], [bit_vars[i]])
            else:
                self.write_pla(num_input, num_bit, onset, 'pla/on.pla')
                cmd = './espresso pla/on.pla > pla/out_on.pla'
                os.system(cmd)
                opt_onset = self.read_pla('pla/out_on.pla')
                for pat in opt_onset:
                    self.pattern2onset_clause(pat, input_vars, sel_combs, bit_vars)

            # offset
            self.write_pla(num_input+num_sel, 1, offset, 'pla/off.pla')
            cmd = './espresso pla/off.pla > pla/out_off.pla'
            os.system(cmd)
            offset = self.read_pla('pla/out_off.pla')
            for pat in offset:
                self.pattern2offset_clause(pat, input_vars, sel_vars)

        elif rep == 'aig':
            # only prob = 1
            if len(onset) == 0 and len(p1_onset) > 0:
                p1_onset = [(p + '0') for p in p1_onset]
                self.write_pla(num_input, 1, p1_onset, 'pla/off.pla')
                cmd = './abc -c \"read_pla -z pla/off.pla; st; ps; %s ps; aig2cnf pla/off.dimacs pla/off.io\"' % (
                    opt_cmd)
                os.system(cmd)
                self.dimacs2offset_clause(input_vars, [], 'pla/off.dimacs',
                                          'pla/off.io', reverse=True)
            # no prob = 1
            elif len(p1_onset) == 0:
                self.write_pla(num_input, num_bit, onset, 'pla/on.pla')
                cmd = './abc -c \"r pla/on.pla; st; ps; %s ps; aig2cnf pla/on.dimacs pla/on.io\"' % (
                    opt_cmd)
                os.system(cmd)
                self.dimacs2onset_clause(input_vars, sel_combs, bit_vars,
                                         'pla/on.dimacs', 'pla/on.io', complement=True)
            else:
                # onset
                self.write_pla(num_input, num_bit, onset, 'pla/on.pla')
                cmd = './abc -c \"r pla/on.pla; st; ps; %s ps; aig2cnf pla/on.dimacs pla/on.io\"' % (
                    opt_cmd)
                os.system(cmd)
                self.dimacs2onset_clause(input_vars, sel_combs, bit_vars,
                                         'pla/on.dimacs', 'pla/on.io')
                # offset
                self.write_pla(num_input, num_bit, offset, 'pla/off.pla')
                cmd = './abc -c \"r pla/off.pla; st; ps; %s ps; aig2cnf pla/off.dimacs pla/off.io\"' % (
                    opt_cmd)
                os.system(cmd)
                self.dimacs2offset_clause(input_vars, sel_combs, 'pla/off.dimacs', 'pla/off.io')
        else:
            raise ValueError('unknown representation', rep)

    def cpt2minterm(self, n, num_bit, num_sel, sel_combs):
        '''
        pattern: alpha state bit
        '''

        total_state_cls = self.node_id2state_cls_full[n.id]
        state_cls = self.node_id2state_cls[n.id]
        num_total_state = len(total_state_cls)
        num_state = n.num_states

        combs_all = self.cal_combination(n, full=True)
        num_total_combs = len(combs_all)

        combs = self.cal_combination(n)
        num_combs = len(combs)

        min_val = max(0.5**num_bit, self.min_val)

        p1_onset = []
        onset = []
        offset = []
        comb_id = 0
        for i in range(num_total_combs):
            comb = combs_all[i]
            if comb_id < num_combs:
                alpha_comb = combs[comb_id]
            else:
                alpha_comb = []
            for j in range(num_total_state):
                state_comb = total_state_cls[j]
                if comb == alpha_comb and j < num_state:
                    prob = n.cpt[comb_id][j]
                else:
                    prob = 0

                # prob = 1
                if prob >= (1 - min_val / 2):
                    pat = self.assign2pattern(comb+state_comb)
                    p1_onset.append(pat)
                    continue
                # onset
                # input: alpha state
                # output: bit
                else:
                    if prob >= min_val / 2:
                        pat = self.assign2pattern(comb+state_comb)
                        bit_pat = self.prob2bit(prob, num_bit)
                        onset.append(pat+bit_pat)
                # offset
                # input: alpha state select
                # output: bit
                if prob >= min_val / 2:
                    for k, sel in enumerate(sel_combs[:num_bit]):
                        if bit_pat[k] == '0':
                            sel_pat = [-v for v in sel]
                            pat = self.assign2pattern(comb+state_comb+sel_pat)
                            offset.append(pat+'1')
                else:
                    pat = self.assign2pattern(comb+state_comb)
                    offset.append(pat + '-'*num_sel + '1')
            if comb == alpha_comb:
                comb_id += 1

        return p1_onset, onset, offset

    def pattern2onset_clause(self, pat, input_vars, sel_combs, bit_vars):
        '''
        alpha state -> bit
        '''
        in_pat, out_pat = pat.strip().split()
        assert (len(in_pat) == len(input_vars))
        assert (len(out_pat) == len(bit_vars))

        in_cl = self.pattern2clause(in_pat, input_vars)
        out_cl = []
        for i, p in enumerate(out_pat):
            if p == '1':
                cl = self.implication(in_cl, sel_combs[i]+[bit_vars[i]])
                self.clauses.append(cl)
                # out_cl.append(bit_vars[i])

        # cl = self.implication(in_cl, out_cl)
        # self.clauses.append(cl)

    def pattern2offset_clause(self, pat, input_vars, sel_vars):
        '''
        alpha state sel' -> false
        '''
        pat = pat.strip().split()[0]
        assert (len(pat) == (len(input_vars) + len(sel_vars)))
        in_pat = pat[:len(input_vars)]
        out_pat = pat[len(input_vars):]

        in_cl = self.pattern2clause(in_pat, input_vars)
        out_cl = self.pattern2clause(out_pat, sel_vars)
        cl = self.implication(in_cl, False) + self.implication(out_cl, False)
        self.clauses.append(cl)

    def pattern2clause(self, pat, vars):
        '''
        01-0: (-1 2 -4)
        '''
        assert (len(pat) == len(vars))

        cl = []
        for i, p in enumerate(pat):
            if p == '1':
                cl.append(vars[i])
            elif p == '0':
                cl.append(-vars[i])
            else:
                pass
        return cl

    def dimacs2onset_clause(self, input_vars, sel_combs, bit_vars, cnf_file, io_file, complement=False):
        num_vars, clauses = self.read_dimacs(cnf_file)
        input_map, output_map = self.read_io(io_file)

        # create new vars for output
        new_output_map = {}
        for key in output_map.keys():
            self.var_id += 1
            id = self.var_id
            self.intro_vars.append(id)
            new_output_map[key] = id
            value = output_map[key]
            # onset
            self.clauses.append([-id] + sel_combs[value] + [bit_vars[value]])
            # offset
            if complement:
                self.clauses.append([id] + sel_combs[value])
        output_map = new_output_map

        intro_map = {}
        for cl in clauses:
            new_cl = []
            for l in cl:
                i = input_map.get(abs(l))
                if i is not None:
                    lit = input_vars[i] if l > 0 else -input_vars[i]
                    new_cl.append(lit)
                    continue
                o = output_map.get(abs(l))
                if o is not None:
                    lit = o if l > 0 else -o
                    new_cl.append(lit)
                    continue
                v = intro_map.get(abs(l))
                if v is not None:
                    lit = v if l > 0 else -v
                    new_cl.append(lit)
                else:
                    self.var_id += 1
                    id = self.var_id
                    self.intro_vars.append(id)
                    intro_map[int(l)] = id
                    lit = id if l > 0 else -id
                    new_cl.append(lit)
            self.clauses.append(new_cl)

    def dimacs2offset_clause(self, input_vars, sel_vars, cnf_file, io_file, reverse=False):
        num_vars, clauses = self.read_dimacs(cnf_file)
        input_map, output_map = self.read_io(io_file)

        assert (len(output_map) == 1)
        key = list(output_map.keys())[0]
        self.var_id += 1
        out_id = self.var_id
        self.intro_vars.append(out_id)
        if not reverse:
            self.clauses.append([-out_id])
        else:
            self.clauses.append([out_id])

        in_vars = input_vars + sel_vars
        intro_map = {}
        for cl in clauses:
            new_cl = []
            for l in cl:
                i = input_map.get(abs(l))
                if i is not None:
                    if i < len(input_vars):
                        lit = in_vars[i] if l > 0 else -in_vars[i]
                    else:
                        lit = -in_vars[i] if l > 0 else in_vars[i]
                    new_cl.append(lit)
                    continue
                if abs(l) == key:
                    lit = out_id if l > 0 else -out_id
                    new_cl.append(lit)
                    continue
                v = intro_map.get(abs(l))
                if v is not None:
                    lit = v if l > 0 else -v
                    new_cl.append(lit)
                else:
                    self.var_id += 1
                    id = self.var_id
                    self.intro_vars.append(id)
                    intro_map[int(l)] = id
                    lit = id if l > 0 else -id
                    new_cl.append(lit)
            self.clauses.append(new_cl)

    def encode_cpt_bit_log_sel(self, n, split_cls=False):
        assert (self.log_state and split_cls) or (not self.log_state)

        num_bit = self.num_bit
        vars = self.node_id2state_vars[n.id]
        if self.log_state:
            state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        min_val = max(0.5**num_bit, self.min_val)

        # conditional probability
        # Find bit representation of each entry
        # Decide the number of select variable
        used_var = [False for i in range(num_bit)]
        entry2bit_id = []
        var_pool = {}
        for i in range(len(n.cpt)):
            row2bit_id = []
            for j in range(len(n.cpt[0])):
                prob = n.cpt[i][j]
                if prob > 1 - min_val / 2:
                    row2bit_id.append(True)
                    continue
                elif prob < min_val / 2:
                    row2bit_id.append(False)
                    continue
                # find whether the prob is calculated
                tp = var_pool.get(round(prob, self.digit))
                if tp is not None:
                    row2bit_id.append(tp[0])
                else:
                    bit_ids = []
                    bit_val = 1
                    p = prob
                    for b in range(num_bit):
                        bit_val *= 0.5
                        if (p >= (bit_val)) or (b == num_bit-1 and p > min_val/2):   # if the bit is 1
                            p -= bit_val
                            used_var[b] = True
                            bit_ids.append(b)
                            # early stop if done
                            if p < min_val / 2:
                                break
                    if not split_cls:
                        row2bit_id.append(bit_ids)
                    else:
                        self.var_id += 1
                        id = self.var_id
                        self.intro_vars.append(id)
                        var_pool[round(prob, self.digit)] = (id, bit_ids)
                        tp = (id, bit_ids)
                        row2bit_id.append(tp[0])
            entry2bit_id.append(row2bit_id)

        # add bit variables
        p = 1
        bit_id2var = [0 for i in range(num_bit)]
        for b in range(num_bit):
            p *= 0.5
            if used_var[b]:
                self.var_id += 1
                id = self.var_id
                self.rand_vars.append((id, p))
                bit_id2var[b] = id

        num_sel, sel_vars, sel_comb = self.add_select_vars(num_bit)

        redunt_sel_num = 2**num_sel - num_bit
        if redunt_sel_num > 0:
            merged = self.merge_state_cls(sel_comb[-redunt_sel_num:])
            self.clauses += merged

        # the clauses (bit_v -> select + rand bits)
        bit_id2cls_var = [0 for i in range(num_bit)]
        if split_cls:
            # redund_sel = []
            for b in range(num_bit):
                if used_var[b]:
                    self.var_id += 1
                    id = self.var_id
                    self.intro_vars.append(id)
                    bit_id2cls_var[b] = id
                    sel = sel_comb[b]
                    self.clauses.append([-id] + sel + [bit_id2var[b]])
            #     else:
            #         redund_sel.append(sel_comb[b])
            # merged = self.merge_state_cls(redund_sel)
            # self.clauses += merged

        # the clauses (shared v -> rand bits)
        if split_cls:
            for (id, bit_ids) in var_pool.values():
                # self.clauses.append([-id] + [bit_id2cls_var[bid] for bid in bit_ids])
                for i, bid in enumerate(bit_ids):
                    rand_v = bit_id2cls_var[bid]
                    self.clauses.append([-id] + [rand_v])
                redund_sel = []
                for i in range(num_bit):
                    if i not in bit_ids:
                        redund_sel.append(sel_comb[i])
                # not used
                merged = self.merge_state_cls(redund_sel)
                for sel in merged:
                    self.clauses.append([-id] + sel)

        # CPT to clauses
        for j, comb in enumerate(combs):
            base_cl = [-v for v in comb]
            # if split_cls:
            #     self.var_id += 1
            #     id = self.var_id
            #     self.intro_vars.append(id)
            #     self.clauses.append(base_cl + [id])
            #     base_cl = [-id]
            bit_val = 1
            false_cls = []
            for i in range(n.num_states):
                # the assignment of this state
                if not self.log_state:
                    s = [vars[i]]
                else:
                    s = state_cls[i]
                bit_ids = entry2bit_id[j][i]
                if bit_ids is True:
                    false_cls = []
                    for v in s:
                        self.clauses.append(base_cl + [v])
                    break
                elif bit_ids is False:
                    false_cls.append(self.implication(s, False))
                else:
                    if not split_cls:
                        for i, id in enumerate(bit_ids):
                            sel = sel_comb[i]
                            rand_v = bit_id2var[id]
                            self.clauses.append(
                                base_cl + self.implication(s, False) + sel + [rand_v])
                        merged = self.merge_state_cls(
                            sel_comb[len(bit_ids):-redunt_sel_num])
                        for sel in merged:
                            self.clauses.append(
                                base_cl + self.implication(s, False) + sel)
                    else:
                        self.clauses.append(
                            base_cl + self.implication(s, False) + [bit_ids])

            for cl in false_cls:
                self.clauses.append(base_cl + cl)

    def encode_cpt_bit_sel(self, n, share_var=True):
        num_bit = self.num_bit
        vars = self.node_id2state_vars[n.id]
        if self.log_state:
            state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        min_val = max(0.5**num_bit, self.min_val)

        # conditional probability
        # Find bit representation of each entry
        # Decide the number of select variable
        used_var = [False for i in range(num_bit)]
        entry2bit_id = []
        var_pool = {}
        var_count = {}
        for i in range(len(n.cpt)):
            row2bit_id = []
            for j in range(len(n.cpt[0])):
                prob = n.cpt[i][j]
                if prob > 1 - min_val / 2:
                    row2bit_id.append(True)
                    continue
                elif prob < min_val / 2:
                    row2bit_id.append(False)
                    continue
                # find whether the prob is calculated
                bit_ids = var_pool.get(round(prob, self.digit))
                if bit_ids is not None:
                    var_count[round(prob, self.digit)] += 1
                    row2bit_id.append(bit_ids)
                else:
                    bit_ids = []
                    bit_val = 1
                    p = prob
                    for b in range(num_bit):
                        bit_val *= 0.5
                        if (p >= (bit_val)) or (b == num_bit-1 and p > min_val/2):   # if the bit is 1
                            p -= bit_val
                            used_var[b] = True
                            bit_ids.append(b)
                            # early stop if done
                            if p < min_val / 2:
                                break
                    row2bit_id.append(bit_ids)
                    var_pool[round(prob, self.digit)] = bit_ids
                    var_count[round(prob, self.digit)] = 1
            entry2bit_id.append(row2bit_id)

        print('Use %d / %d bits' % (sum(used_var), num_bit))
        # add bit variables and sel variables
        p = 1
        bit_id2var = [0 for i in range(num_bit)]
        sel_var = []
        for b in range(num_bit):
            p *= 0.5
            if used_var[b]:
                # bit vars
                self.var_id += 1
                id = self.var_id
                self.rand_vars.append((id, -1))
                bit_id2var[b] = id
                # self.scale *= 2

                # clause: cannot be both 1
                for i in range(b):
                    if used_var[i]:
                        self.clauses.append([-bit_id2var[i], -id])

                # sel vars
                self.var_id += 1
                sid = self.var_id
                self.rand_vars.append((sid, p))
                sel_var.append(sid)

                # clause: b1 -> r1
                self.clauses.append([-id, sid])

        # add prob variables
        if share_var:
            for p in list(var_pool.keys()):
                if var_count[p] > self.thr_shared_num and isinstance(var_pool[p], list):
                    # self.var_id += 1
                    # id = self.var_id
                    # self.rand_vars.append((id, -1))
                    self.var_id += 1
                    vid = self.var_id
                    self.rand_vars.append((vid, p))
                    var_pool[p] = vid
                    # self.clauses.append([-id, vid])
                    # for i in range(b):
                    #     if used_var[i]:
                    #         self.clauses.append([-bit_id2var[i], -id])

        # CPT to clauses
        shared_num = 0
        for j, comb in enumerate(combs):
            base_cl = [-v for v in comb]
            false_cls = []
            for i in range(n.num_states):
                # the assignment of this state
                if not self.log_state:
                    s = [vars[i]]
                else:
                    s = state_cls[i]

                bit_ids = entry2bit_id[j][i]
                if bit_ids is True:
                    false_cls = []
                    for v in s:
                        self.clauses.append(base_cl + [v])
                    break
                elif bit_ids is False:
                    false_cls.append(self.implication(s, False))
                else:
                    cl = base_cl + self.implication(s, False)
                    if not share_var:
                        for id in bit_ids:
                            cl.append(bit_id2var[id])
                    else:
                        prob = n.cpt[j][i]
                        var_ids = var_pool[round(prob, self.digit)]
                        if isinstance(var_ids, list):
                            for id in var_ids:
                                cl.append(bit_id2var[id])
                        else:
                            shared_num += 1
                            cl.append(var_ids)
                    self.clauses.append(cl)
            # merged = self.merge_state_cls(false_cls)
            # for cl in merged:
            for cl in false_cls:
                self.clauses.append(base_cl + cl)

        if share_var:
            print('Shared num =', shared_num, '/', len(n.cpt)*len(n.cpt[0]))

    def encode_cpt_bit_bad(self, n, split_cls=False):
        assert (self.log_state and split_cls) or (not self.log_state)

        num_bit = self.num_bit
        vars = self.node_id2state_vars[n.id]
        if self.log_state:
            state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        min_val = max(0.5**num_bit, self.min_val)

        # conditional probability
        # Find bit representation of each entry
        # Decide the number of select variable
        used_var = [False for i in range(num_bit)]
        max_used = 0    # maximum num of rand vars for a single entry
        entry2bit_id = []
        var_pool = {}
        for i in range(len(n.cpt)):
            row2bit_id = []
            for j in range(len(n.cpt[0])):
                prob = n.cpt[i][j]
                if prob > 1 - min_val / 2:
                    row2bit_id.append(True)
                    continue
                elif prob < min_val / 2:
                    row2bit_id.append(False)
                    continue
                bit_ids = []
                bit_val = 1
                num_used = 0
                p = prob
                for b in range(num_bit):
                    bit_val *= 0.5
                    if (p >= (bit_val)) or (b == num_bit-1 and p > min_val/2):   # if the bit is 1
                        p -= bit_val
                        used_var[b] = True
                        bit_ids.append(b)
                        num_used += 1
                        # early stop if done
                        if p < min_val / 2:
                            break
                max_used = max(max_used, num_used)
                if not split_cls:
                    row2bit_id.append(bit_ids)
                else:
                    tp = var_pool.get(round(prob, self.digit))
                    # if va is None:
                    #     va = var_pool.get(round(1-prob, self.digit))
                    #     if va is not None:
                    #         va = -va
                    if tp is None:
                        self.var_id += 1
                        id = self.var_id
                        self.intro_vars.append(id)
                        var_pool[round(prob, self.digit)] = (id, bit_ids)
                        tp = (id, bit_ids)
                    row2bit_id.append(tp[0])
            entry2bit_id.append(row2bit_id)

        # add bit variables
        p = 1
        bit_id2var = [0 for i in range(num_bit)]
        for b in range(num_bit):
            p *= 0.5
            if used_var[b]:
                self.var_id += 1
                id = self.var_id
                self.rand_vars.append((id, p))
                bit_id2var[b] = id

        # add select variables
        num_sel = math.ceil(math.log(max_used, 2))
        self.scale *= (2**num_sel)

        sel_vars = []
        sel_state = []
        for i in range(num_sel):
            self.var_id += 1
            id = self.var_id
            self.rand_vars.append((id, 0.5))
            sel_vars.append(id)
            sel_state.append([id, -id])
        sel_comb = itertools.product(*sel_state)
        sel_comb = [list(s) for s in sel_comb]

        redunt_sel_num = 2**num_sel - max_used
        if redunt_sel_num > 0:
            merged = self.merge_state_cls(sel_comb[-redunt_sel_num:])
            self.clauses += merged

        # the clauses (shared v -> rand bits)
        if split_cls:
            for (id, bit_ids) in var_pool.values():
                for i, bid in enumerate(bit_ids):
                    sel = sel_comb[i]
                    rand_v = bit_id2var[bid]
                    self.clauses.append([-id] + sel + [rand_v])
                merged = self.merge_state_cls(sel_comb[len(bit_ids):])
                for sel in merged:
                    self.clauses.append([-id] + sel)

        # CPT to clauses
        for j, comb in enumerate(combs):
            base_cl = [-v for v in comb]
            # if split_cls:
            #     self.var_id += 1
            #     id = self.var_id
            #     self.intro_vars.append(id)
            #     self.clauses.append(base_cl + [id])
            #     base_cl = [-id]
            bit_val = 1
            false_cls = []
            for i in range(n.num_states):
                # the assignment of this state
                if not self.log_state:
                    s = [vars[i]]
                else:
                    s = state_cls[i]
                bit_ids = entry2bit_id[j][i]
                if bit_ids is True:
                    false_cls = []
                    for v in s:
                        self.clauses.append(base_cl + [v])
                    break
                elif bit_ids is False:
                    false_cls.append(self.implication(s, False))
                else:
                    if not split_cls:
                        for i, id in enumerate(bit_ids):
                            sel = sel_comb[i]
                            rand_v = bit_id2var[id]
                            self.clauses.append(
                                base_cl + self.implication(s, False) + sel + [rand_v])
                        merged = self.merge_state_cls(
                            sel_comb[len(bit_ids):-redunt_sel_num])
                        for sel in merged:
                            self.clauses.append(
                                base_cl + self.implication(s, False) + sel)
                    else:
                        self.clauses.append(
                            base_cl + self.implication(s, False) + [bit_ids])

            for cl in false_cls:
                self.clauses.append(base_cl + cl)

    def encode_cpt_bit_sub(self, n, split_cls=False):
        num_bit = self.num_bit
        vars = self.node_id2state_vars[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        # add variables
        p = 1
        rand_vars = []
        for b in range(num_bit):
            p *= 0.5
            self.var_id += 1
            id = self.var_id
            self.rand_vars.append((id, p))
            rand_vars.append(id)
        min_val = max(p, self.min_val)

        # to have clause sharing
        var_pool = {}

        # conditional probability
        max_num_vars = 0
        for j, comb in enumerate(combs):
            base_cl = [-v for v in comb]
            if split_cls:
                self.var_id += 1
                id = self.var_id
                self.intro_vars.append(id)
                self.clauses.append(base_cl + [id])
                base_cl = [-id]
            bit_val = 1
            for i, v in enumerate(vars):
                prob = n.cpt[j][i]
                if prob > 1 - min_val / 2:
                    cl = base_cl + [v]
                    self.clauses.append(cl)
                elif prob < min_val / 2:
                    # cl = base_cl + [-v]
                    pass
                else:
                    # find variables to share
                    va = var_pool.get(prob)
                    if va is None:
                        self.var_id += 1
                        va = self.var_id
                        self.intro_vars.append(va)
                        var_pool[prob] = va

                        cl = [-va]
                        bit_val = 1
                        for b in range(num_bit):
                            bit_val *= 0.5
                            if prob >= (bit_val - min_val/2):   # if the bit is 1
                                prob -= bit_val
                                cl.append(rand_vars[b])
                                self.clauses.append([-rand_vars[b], va])
                                # early stop if done
                                if prob < min_val / 2:
                                    max_num_vars = max(max_num_vars, b+1)
                                    break
                        # self.clauses.append(cl)

                    cl = base_cl + [-va] + [v]
                    self.clauses.append(cl)

        # remove variables not used
        for i in range(num_bit - max_num_vars):
            self.var_id -= 1
            self.rand_vars.pop()

    def encode_cpt_bit05_old(self, n, split_cls=False):
        assert (self.log_state and split_cls) or (not self.log_state)

        vars = self.node_id2state_vars[n.id]
        if self.log_state:
            state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        num_bit = self.find_max_bit(n)

        rand_vars = []
        for b in range(num_bit):
            self.var_id += 1
            id = self.var_id
            self.rand_vars.append((id, 0.5))
            rand_vars.append(id)
        max_num_vars = 0

        # conditional probability
        for j, comb in enumerate(combs):
            base_cl = [-v for v in comb]
            vals = n.cpt[j].copy()
            bit_val = 1
            cur_comb = []   # record the current combination of rand vars
            prob = 0

            # import pdb
            # pdb.set_trace()
            for b in range(num_bit):
                bit_val *= 0.5
                for i in range(n.num_states):
                    if not self.log_state:
                        s = [vars[i]]
                    else:
                        s = state_cls[i]
                    val = vals[i]
                    cl = []
                    if val == 1:
                        cl = base_cl + s
                        prob = 1
                    elif val == 0:
                        # cl = base_cl + self.implication(s, False)
                        pass
                    elif val >= bit_val:   # if the bit is 1
                        vals[i] = val - bit_val
                        prob += bit_val
                        # get the combination of rand vars
                        cur_comb = self.assign_prob_comb(rand_vars, b+1, cur_comb)
                        cl = base_cl + s + [-y for y in cur_comb]
                    # import pdb
                    # pdb.set_trace()
                    if len(cl) != 0:
                        self.clauses.append(cl)
                if prob >= 1:
                    break

    '''
    Maybe works!!!!
    '''

    def encode_cpt_bit05(self, n, split_cls=False):
        assert (self.log_state and split_cls) or (not self.log_state)

        num_bit = self.num_bit
        vars = self.node_id2state_vars[n.id]
        if self.log_state:
            state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        min_val = max(0.5**num_bit, self.min_val)

        # conditional probability
        # Find bit representation of each entry
        # Decide the number of select variable
        used_var = [False for i in range(num_bit)]
        max_used = 0    # maximum num of rand vars for a single entry
        entry2bit_id = []
        var_pool = {}
        for i in range(len(n.cpt)):
            row2bit_id = []
            for j in range(len(n.cpt[0])):
                prob = n.cpt[i][j]
                if prob > 1 - min_val / 2:
                    row2bit_id.append(True)
                    continue
                elif prob < min_val / 2:
                    row2bit_id.append(False)
                    continue
                bit_ids = []
                bit_val = 1
                num_used = 0
                p = prob
                for b in range(num_bit):
                    bit_val *= 0.5
                    if (p >= (bit_val)) or (b == num_bit-1 and p > min_val/2):   # if the bit is 1
                        p -= bit_val
                        used_var[b] = True
                        bit_ids.append(b)
                        num_used += 1
                        # early stop if done
                        if p < min_val / 2:
                            break
                max_used = max(max_used, num_used)
                if not split_cls:
                    row2bit_id.append(bit_ids)
                else:
                    tp = var_pool.get(round(prob, self.digit))
                    # if va is None:
                    #     va = var_pool.get(round(1-prob, self.digit))
                    #     if va is not None:
                    #         va = -va
                    if tp is None:
                        self.var_id += 1
                        id = self.var_id
                        self.intro_vars.append(id)
                        var_pool[round(prob, self.digit)] = (id, bit_ids)
                        tp = (id, bit_ids)
                    row2bit_id.append(tp[0])
            entry2bit_id.append(row2bit_id)

        # add bit variables
        p = 1
        bit_id2var = [0 for i in range(num_bit)]
        for b in range(num_bit):
            p *= 0.5
            if used_var[b]:
                self.var_id += 1
                id = self.var_id
                self.rand_vars.append((id, p))
                bit_id2var[b] = id

        # add select variables
        num_sel = math.ceil(math.log(max_used, 2))
        self.scale *= (2**num_sel)

        sel_vars = []
        sel_state = []
        for i in range(num_sel):
            self.var_id += 1
            id = self.var_id
            self.rand_vars.append((id, 0.5))
            sel_vars.append(id)
            sel_state.append([id, -id])
        sel_comb = itertools.product(*sel_state)
        sel_comb = [list(s) for s in sel_comb]

        redunt_sel_num = 2**num_sel - max_used
        if redunt_sel_num > 0:
            merged = self.merge_state_cls(sel_comb[-redunt_sel_num:])
            self.clauses += merged

        # the clauses (shared v -> rand bits)
        if split_cls:
            for (id, bit_ids) in var_pool.values():
                for i, bid in enumerate(bit_ids):
                    sel = sel_comb[i]
                    rand_v = bit_id2var[bid]
                    self.clauses.append([-id] + sel + [rand_v])
                merged = self.merge_state_cls(sel_comb[len(bit_ids):])
                for sel in merged:
                    self.clauses.append([-id] + sel)

        # CPT to clauses
        for j, comb in enumerate(combs):
            base_cl = [-v for v in comb]
            if split_cls:
                self.var_id += 1
                id = self.var_id
                self.intro_vars.append(id)
                self.clauses.append(base_cl + [id])
                base_cl = [-id]
            bit_val = 1
            false_cls = []
            for i in range(n.num_states):
                # the assignment of this state
                if not self.log_state:
                    s = [vars[i]]
                else:
                    s = state_cls[i]
                bit_ids = entry2bit_id[j][i]
                if bit_ids is True:
                    false_cls = []
                    for v in s:
                        self.clauses.append(base_cl + [v])
                    break
                elif bit_ids is False:
                    false_cls.append(self.implication(s, False))
                else:
                    if not split_cls:
                        for i, id in enumerate(bit_ids):
                            sel = sel_comb[i]
                            rand_v = bit_id2var[id]
                            self.clauses.append(
                                base_cl + self.implication(s, False) + sel + [rand_v])
                        merged = self.merge_state_cls(
                            sel_comb[len(bit_ids):-redunt_sel_num])
                        for sel in merged:
                            self.clauses.append(
                                base_cl + self.implication(s, False) + sel)
                    else:
                        self.clauses.append(
                            base_cl + self.implication(s, False) + [bit_ids])

            for cl in false_cls:
                self.clauses.append(base_cl + cl)

    def cal_combination(self, n, full=False):
        assert (not full) or (self.log_state and full)

        args = []
        for r in n.parents:
            if not self.log_state:
                s = self.node_id2state_vars[r.id]
            else:
                if not full:
                    s = self.node_id2state_cls[r.id]
                else:
                    s = self.node_id2state_cls_full[r.id]
            args.append(s)

        comb = itertools.product(*args)
        new_combs = [c for c in comb]

        if self.log_state:
            log_combs = []
            for c in new_combs:
                new_c = []
                for cl in c:
                    new_c += cl
                log_combs.append(new_c)
            if len(new_combs) == 0:
                log_combs = [()]
            new_combs = log_combs

        return new_combs

    def get_combination_vars(self, n):
        parent_vars = []
        for r in n.parents:
            if not self.log_state:
                s = self.node_id2state_vars[r.id]
                parent_vars = s
            else:
                s = self.node_id2state_cls[r.id]
                for v in s[0]:
                    parent_vars.append(abs(v))

        node_vars = []
        s = self.node_id2state_cls[n.id]
        for v in s[0]:
            node_vars.append(abs(v))
        return parent_vars, node_vars

    def assign_prob_comb(self, rand_vars, b, cur_comb):
        '''
        rand_vars: [y1, y2, ...] with 0.5 probs
        b: the bth bit is 1
        cur_comb: the last combination given
        '''
        # import pdb
        # pdb.set_trace()
        if cur_comb == []:
            new_comb = []
            for i in range(b):
                new_comb.append(-rand_vars[i])
        else:
            new_comb = self.comb_count(rand_vars, cur_comb)
            if b > len(cur_comb):
                for i in range(len(cur_comb), b):
                    new_comb.append(-rand_vars[i])

        return new_comb

    def comb_count(self, rand_vars, comb):
        bit_str = ''
        for v in comb:
            if v < 0:
                bit_str += '0'
            else:
                bit_str += '1'
        num = int(bit_str, 2)
        num += 1

        new_comb = []
        bit_str = '{0:b}'.format(num)
        # amend the number of bit
        for i in range(len(bit_str), len(comb)):
            bit_str = '0' + bit_str

        for i, b in enumerate(bit_str):
            if b == '0':
                new_comb.append(-rand_vars[i])
            else:
                new_comb.append(rand_vars[i])
        return new_comb

    def encode_observe(self, n):
        self.node_id2ob_vars[n.id] = []
        if not self.log_state:
            for p in n.parents:
                if p.kind == 'chance':
                    pr = 1
                    base_cl = []
                    vars = self.node_id2state_vars[p.id]
                    for i, v in enumerate(vars):
                        if i != len(vars)-1:
                            self.var_id += 1
                            id = self.var_id
                            prob = (1/len(vars)) / pr  # normalize
                            pr -= 1/len(vars)
                            self.ob_vars.append((id, prob))
                            self.node_id2ob_vars[n.id].append((id, prob))

                            if len(base_cl) != 0:
                                base_cl[-1] = -base_cl[-1]
                            base_cl.append(-id)
                            self.clauses.append(base_cl + [v])
                        else:
                            if len(base_cl) != 0:
                                base_cl[-1] = -base_cl[-1]
                            self.clauses.append(base_cl + [v])

                    self.scale *= p.num_states
        else:
            for p in n.parents:
                if p.kind != 'chance':
                    continue
                vars = self.node_id2state_vars[p.id]
                ob_vars = [v for (v, _) in self.ob_vars]
                for i, v in enumerate(vars):
                    if self.causal:
                        self.var_id += 1
                        id = self.var_id
                        # if v not in ob_vars:
                        self.ob_vars.append((id, 0.5))
                        self.node_id2ob_vars[n.id].append((id, 0.5))
                        self.clauses.append([v, -id])
                        self.clauses.append([-v, id])
                        self.scale *= 2
                    else:
                        if v not in ob_vars:
                            self.ob_vars.append((v, 0.5))
                            self.node_id2ob_vars[n.id].append((v, 0.5))
                            self.scale *= 2

    def encode_util_val(self, n):
        merge_list = self.util2merge_list(n)
        merge_list = self.simplify_merge_list(merge_list)
        vars = self.util_state_vars.copy()
        for r in n.parents:
            if not self.log_state:
                s = self.node_id2state_vars[r.id]
                vars += s
            else:
                s = self.node_id2state_cls[r.id]
                for v in s[0]:
                    vars.append(abs(v))

        self.encode_merge_list(n, merge_list, vars)

    def encode_super_util(self, n):
        combs = self.cal_combination(n)

        assert (len(combs) == len(n.vals)), (len(combs), len(n.vals))

        # find max and min
        self.max_util = n.vals[0]
        self.min_util = n.vals[0]
        for val in n.vals[1:]:
            self.max_util = max(self.max_util, val)
            self.min_util = min(self.min_util, val)

        for i, comb in enumerate(combs):
            val = n.vals[i]
            prob = (val - self.min_util) / (self.max_util - self.min_util)
            base_cl = [-c for c in comb]
            if prob == 1:
                pass
            elif prob == 0:
                self.clauses.append(base_cl)
            else:
                self.var_id += 1
                id = self.var_id
                self.util_vars.append((id, prob))
                cl = base_cl + [id]
                self.clauses.append(cl)

    def encode_util_bit(self, n):
        combs = self.cal_combination(n)

        assert (len(combs) == len(n.vals)), (len(combs), len(n.vals))

        for i, comb in enumerate(combs):
            pass

    def implication(self, assign, cl):
        '''
        assignment -> clause as CNF
        -assignment | cl2
        '''
        assert(assign != False and cl != True)

        if assign == True:
            return cl

        new_cl = []
        for v in assign:
            new_cl.append(-v)

        if cl == False:
            return new_cl

        for v in cl:
            new_cl.append(v)

        return new_cl

    def merge_state_cls(self, clauses, dc_clauses=[]):
        remain_clauses = clauses.copy() + dc_clauses.copy()
        final_clauses = []

        # assume all the clauses are sorted by vars
        while len(remain_clauses) > 0:
            new_clauses = []
            is_merged_id = []
            for i, cl1 in enumerate(remain_clauses):
                for j in range(i+1, len(remain_clauses)):
                    cl2 = remain_clauses[j]
                    if len(cl1) != len(cl2):
                        continue

                    # compare
                    num_diff = 0
                    can_merge = False
                    merge_cl = []
                    for k, v1 in enumerate(cl1):
                        v2 = cl2[k]
                        # have different literal
                        if abs(v1) != abs(v2):
                            can_merge = False
                            break
                        # if same phase
                        elif v1 == v2:
                            continue
                        # not the same phase
                        else:
                            num_diff += 1
                            # if >2 not the same, cannot merge
                            if num_diff > 1:
                                can_merge = False
                                break

                            can_merge = True
                            merge_cl = cl1.copy()
                            merge_cl.remove(v1)

                    # the merged clause
                    if can_merge:
                        if i not in is_merged_id:
                            is_merged_id.append(i)
                        if j not in is_merged_id:
                            is_merged_id.append(j)
                        new_clauses.append(merge_cl)
            # cannot be merged anymore
            for i, cl in enumerate(remain_clauses):
                if i in is_merged_id:
                    continue
                if (remain_clauses[i] not in final_clauses) and (remain_clauses[i] not in dc_clauses):
                    final_clauses.append(remain_clauses[i])
            # clauses for next iteration
            remain_clauses = new_clauses
        return final_clauses

    def assign2pattern(self, alpha):
        pattern = ''
        for v in alpha:
            if v > 0:
                pattern += '1'
            else:
                pattern += '0'
        return pattern

    def prob2bit(self, prob, num_bit):
        min_val = max(0.5**num_bit, self.min_val)

        bit_pat = ''
        bit_val = 1
        p = prob
        for b in range(num_bit):
            bit_val *= 0.5
            if (p >= (bit_val)) or (b == num_bit-1 and p > min_val/2):   # if the bit is 1
                p -= bit_val
                bit_pat += '1'
                # early stop if done
                if p < min_val / 2:
                    for bb in range(b+1, num_bit):
                        bit_pat += '0'
                    break
            else:
                bit_pat += '0'

        return bit_pat

    def count_bits(self, bit_pat):
        count = 0
        for i, b in enumerate(bit_pat):
            if b == '1':
                count = i + 1
        return count

    def write_pla(self, num_input, num_output, patterns, filename):
        f = open(filename, 'w')
        f.write('.i %d\n' % (num_input))
        f.write('.o %d\n' % (num_output))
        # f.write('.type f\n')
        for p in patterns:
            f.write(p[:num_input])
            f.write(' ')
            f.write(p[num_input:])
            f.write('\n')
        f.write('.e\n')

    def read_pla(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        patterns = []
        for line in lines:
            if line[0] != '.':
                patterns.append(line)

        return patterns

    def add_bit_vars(self, num_bit):
        bit_vars = []
        p = 1
        for i in range(num_bit):
            p *= 0.5
            self.var_id += 1
            id = self.var_id
            bit_vars.append(id)
            self.rand_vars.append((id, p))
        return bit_vars

    def add_select_vars(self, num_bit, imply_rand=True):
        if num_bit == 0:
            return 0, [], []
        num_sel = math.ceil(math.log(num_bit, 2))
        self.scale *= (2**num_sel)

        sel_vars = []
        sel_state = []
        for i in range(num_sel):
            self.var_id += 1
            id = self.var_id
            self.rand_vars.append((id, -1))
            sel_vars.append(id)
            sel_state.append([id, -id])
        sel_comb = itertools.product(*sel_state)
        sel_comb = [list(s) for s in sel_comb]

        if imply_rand:
            for i in range(num_bit, 2**num_sel):
                self.clauses.append(sel_comb[i])

        return num_sel, sel_vars, sel_comb

    def map_bit_sel(self, bit_vars, sel_combs):
        # the clauses (bit_v -> select + rand bits)
        new_bit_vars = []
        for i, v in enumerate(bit_vars):
            self.var_id += 1
            id = self.var_id
            self.intro_vars.append(id)
            new_bit_vars.append(id)
            sel = sel_combs[i]
            self.clauses.append([-id] + sel + [v])

        return new_bit_vars

    def read_dimacs(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        num_vars = 0
        num_cls = 0
        clauses = []
        max_var = 0
        for line in lines:
            if line[0] == 'c':
                continue
            elif len(line) == 1:
                continue
            elif line[0] == 'p':
                pars = line.strip().split()
                num_vars = int(pars[2])
                num_cls = int(pars[3])
            else:
                pars = line.strip().split()
                cl = []
                for p in pars[:-1]:
                    cl.append(int(p))
                    max_var = max(max_var, abs(int(p)))
                clauses.append(cl)

        # make sure from 1 to num_vars
        assert max_var <= num_vars

        return num_vars, clauses

    def read_io(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        info = lines[0].strip().split()
        num_inputs = int(info[1])
        num_outputs = int(info[2])

        input_map = {}
        for i in range(num_inputs):
            line = lines[2+i]
            pars = line.strip().split()
            input_map[int(pars[1])] = int(pars[0])

        output_map = {}
        for i in range(num_outputs):
            line = lines[3+num_inputs+i]
            pars = line.strip().split()
            output_map[int(pars[1])] = int(pars[0])

        return input_map, output_map

    def cpt2merge_list(self, n, seperate_state=False):
        '''
        merge list = 
        [
            ([pat1], prob1),
            ([pat2], prob2),
            ...
        ]

        pat = ['0000', '10-1', ...]

        seperate_state: merge each state seperately (bklm16)
        '''

        assert self.log_state

        state_cls = self.node_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert len(n.cpt) == len(combs), (len(n.cpt), len(combs))
        assert len(n.cpt[0]) == n.num_states, (len(n.cpt[0]), n.num_states)

        # to have variable sharing
        if not seperate_state:
            merge_list = {}
        else:
            merge_list = [{} for i in range(n.num_states)]

        # conditional probability
        for j, comb in enumerate(combs):
            p = 1
            base_cl = [-v for v in comb]
            # encode each value in a row
            for i in range(n.num_states):
                prob = n.cpt[j][i]
                if prob == 1:
                    continue
                s = state_cls[i]
                pat = self.assign2pattern(base_cl + self.implication(s, False))

                # find variables with same/complement probability to share
                if not seperate_state:
                    pats = merge_list.get(round(prob, self.digit))
                    if pats is None:
                        merge_list[round(prob, self.digit)] = [pat]
                    else:
                        pats.append(pat)
                else:
                    pats = merge_list[i].get(round(prob, self.digit))
                    if pats is None:
                        merge_list[i][round(prob, self.digit)] = [pat]
                    else:
                        pats.append(pat)

        return merge_list

    def util2merge_list(self, n):
        state_cls = self.util_id2state_cls[n.id]
        combs = self.cal_combination(n)

        assert (len(combs) == len(n.vals)), (len(combs), len(n.vals))

        merge_list = {}
        # conditional probability
        for j, comb in enumerate(combs):
            base_cl = [-v for v in comb]

            prob = n.vals[j]
            if prob == 1:
                continue

            pat = self.assign2pattern(state_cls + base_cl)

            # find variables with same probability to share
            pats = merge_list.get(round(prob, self.digit))
            if pats is None:
                merge_list[round(prob, self.digit)] = [pat]
            else:
                pats.append(pat)

        return merge_list

    def simplify_merge_list(self, merge_list):
        if self.opt == 'none':
            return merge_list

        new_merge_list = {}
        for (prob, pats) in merge_list.items():
            if self.opt == 'qm':
                onset = self.qm_simplify(pats)
            elif self.opt == 'esp':
                onset = self.esp_simplify(pats)
            new_merge_list[prob] = onset

        return new_merge_list

    def qm_simplify(self, patterns):
        if len(patterns) == 0:
            return []

        num_vars = len(patterns[0])

        nums = []
        for pat in patterns:
            nums.append(self.pat2num(pat))

        res = QuineMcCluskey().simplify(nums, num_bits=num_vars)
        return list(res)

    def esp_simplify(self, patterns):
        if len(patterns) == 0:
            return []

        if len(patterns) == 1:
            return patterns

        num_input = len(patterns[0])
        new_pats = [pat+'1' for pat in patterns]

        stamp = str(os.getpid()) + '-' + str(datetime.datetime.now().timestamp())

        self.write_pla(num_input, 1, new_pats, 'pat-%s.pla' % stamp)
        cmd = './espresso pat-%s.pla > out_pat-%s.pla' % (stamp, stamp)
        os.system(cmd)
        opt_onset = self.read_pla('out_pat-%s.pla' % stamp)
        os.system('rm pat-%s.pla out_pat-%s.pla' % (stamp, stamp))
        patterns = [pat[:num_input] for pat in opt_onset]
        return patterns

    def pat2num(self, pat):
        return int(pat, 2)

    def encode_merge_list(self, n, merge_list, vars, sel_var=None, share_neg=False):
        base_cl = []
        # if n.not_depend_d:
        #     base_cl = [-self.thr_var]
        # for v in self.node_id2state_vars[n.id]:
        #     self.var_id += 1
        #     id = self.var_id
        #     self.rand_vars.append((id, 0.5))
        #     self.clauses.append([self.thr_var, id])

        var_pool = {}
        for prob, pats in merge_list.items():
            assert len(vars) == len(pats[0])

            if prob > 1 - self.min_val / 2:
                continue
            elif prob < self.min_val / 2:
                for pat in pats:
                    alpha = self.pattern2clause(pat, vars)
                    self.clauses.append(base_cl+alpha)
                    if sel_var is not None:
                        self.clauses.append(base_cl+alpha+[sel_var])
            else:
                va = var_pool.get(round(prob, self.digit))
                if va is None:
                    if share_neg:
                        va = var_pool.get(round(1-prob, self.digit))
                        if va is None:
                            self.var_id += 1
                            id = self.var_id
                            self.rand_vars.append((id, prob))
                            var_pool[round(prob, self.digit)] = id
                            va = id
                        else:
                            va = -va
                    else:
                        if self.share_val:
                            va = self.share_parent_var(n, prob, pats, vars)
                            if va is None:
                                self.var_id += 1
                                id = self.var_id
                                self.rand_vars.append((id, prob))
                                var_pool[round(prob, self.digit)] = id
                                va = id
                        else:
                            self.var_id += 1
                            id = self.var_id
                            self.rand_vars.append((id, prob))
                            var_pool[round(prob, self.digit)] = id
                            va = id

                for pat in pats:
                    alpha = self.pattern2clause(pat, vars)
                    self.clauses.append(base_cl+alpha + [va])
                    if sel_var is not None:
                        self.clauses.append(base_cl+alpha+[sel_var])

        return var_pool

    def bit_share_merge_list(self, merge_list):
        new_merge_list = {}
        onset_merge_list = {}
        offset_merge_list = {}
        for (prob, pats) in merge_list.items():
            # if len(pats) > self.thr_shared_num:
            #     new_merge_list[prob] = pats.copy()
            #     continue

            bits = self.prob2bit(prob, self.num_bit)
            for i, b in enumerate(bits):
                pr = 0.5**(i+1)
                # import pdb
                # pdb.set_trace()
                if b == '1':
                    bit_pats = onset_merge_list.get(round(pr, self.digit))
                    if bit_pats is None:
                        onset_merge_list[round(pr, self.digit)] = pats.copy()
                    else:
                        onset_merge_list[round(pr, self.digit)] += pats.copy()
                elif b == '0':
                    bit_pats = offset_merge_list.get(round(pr, self.digit))
                    if bit_pats is None:
                        offset_merge_list[round(pr, self.digit)] = pats.copy()
                    else:
                        offset_merge_list[round(pr, self.digit)] += pats.copy()

        return new_merge_list, onset_merge_list, offset_merge_list

    def encode_bit_merge_list(self, n, onset_merge_list, offset_merge_list, vars, imply_rand=True):
        assert len(onset_merge_list) <= self.num_bit
        assert len(offset_merge_list) <= self.num_bit

        num_bit = self.find_max_bit(n)
        bit_vars = self.add_bit_vars(num_bit)
        num_sel, sel_vars, sel_combs = self.add_select_vars(num_bit, imply_rand=imply_rand)

        num_cur_var = len(self.node_id2state_vars[n.id])

        for i in range(num_bit):
            prob = 0.5**(i+1)
            pats = onset_merge_list.get(round(prob, self.digit))
            if pats is None:
                continue
            for pat in pats:
                alpha = self.pattern2clause(pat, vars)
                if imply_rand:
                    self.clauses.append(alpha + [bit_vars[i]] + sel_combs[i])
                else:
                    cl = alpha[:-num_cur_var] + [-bit_vars[i]] + \
                        self.implication(sel_combs[i], False)
                    if len(alpha) > 0:
                        for v in alpha[-num_cur_var:]:
                            self.clauses.append(cl + [-v])
                    else:
                        self.clauses.append(cl)

        for i in range(num_bit):
            prob = 0.5**(i+1)
            pats = offset_merge_list.get(round(prob, self.digit))
            if pats is None:
                continue
            for pat in pats:
                alpha = self.pattern2clause(pat, vars)
                if imply_rand:
                    self.clauses.append(alpha + sel_combs[i])

    def find_max_bit(self, n):
        max_num_bits = 0
        for i in range(len(n.cpt)):
            for j in range(len(n.cpt[0])):
                val = n.cpt[i][j]
                if val == 1:
                    continue
                bit_str = self.prob2bit(val, self.num_bit)
                used_bit = self.count_bits(bit_str)
                max_num_bits = max(max_num_bits, used_bit)

        return max_num_bits

    def share_parent_var(self, n, prob, pats, vars):
        va = None
        for p in n.parents:
            va = self.node_id2var_pool[p.id].get(round(prob, self.digit))
            if va is not None:
                parent_pats = self.node_id2merge_list[p.id].get(round(prob, self.digit))
                parent_vars = self.node_id2vars[p.id]
                if self.check_pats_orthogonal(pats, vars, parent_pats, parent_vars):
                    return va
                else:
                    va = None
        return va

    def check_pats_orthogonal(self, pats1, vars1,  pats2, vars2):
        for pat1 in pats1:
            alpha1 = self.pattern2clause(pat1, vars1)
            for pat2 in pats2:
                alpha2 = self.pattern2clause(pat2, vars2)
                if not self.check_orthogonal(alpha1, alpha2):
                    return False
        return True

    def check_orthogonal(self, alpha1, alpha2):
        for l in alpha1:
            if l in alpha2:
                continue
            elif -l in alpha2:
                return True
        return False
