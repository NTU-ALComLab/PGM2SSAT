import os


class SSATWriter:
    def __init__(self, encoder):
        self.encoder = encoder
        self.net = encoder.net

    def write_ssat(self, filename):
        if self.net.kind == 'BN':
            if self.net.query == 'PE':
                self.write_ssat_re(filename)
            elif self.net.query == 'MPE':
                self.write_ssat_mpe_er(filename)
            elif self.net.query == 'MAP':
                self.write_ssat_map_er(filename)
            elif self.net.query == 'SDP':
                self.write_ssat_sdp_rer(filename)

        elif self.net.kind == 'ID':
            self.write_ssat_id(filename)

        elif self.net.kind == 'CPT':
            self.write_ssat_re(filename)

        else:
            raise ValueError('Unknown net type', self.net.kind)

    def write_ssat_re(self, filename):
        name, ext = os.path.splitext(filename)
        if ext != '.ssat' and ext != '.sdimacs':
            raise ValueError('Unknown extension %s' % (ext))

        print('Filename =', filename)

        f = open(filename, 'w')
        var_num = len(self.encoder.state_vars) + \
            len(self.encoder.rand_vars) + len(self.encoder.intro_vars)
        clause_num = len(self.encoder.clauses)

        if ext == '.ssat':
            f.write('%d\n' % (var_num))
            f.write('%d\n' % (clause_num))
        elif ext == '.sdimacs':
            f.write('p cnf %d %d\n' % (var_num, clause_num))

        evid_vars = []
        for (node_id, state) in self.net.evids:
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2:
                evid_vars.append(vars[1])
            else:
                evid_vars += vars

        r1 = 0
        var_scale = 0
        for id in self.encoder.state_vars:
            if id not in evid_vars:
                write_rand_var(f, id, 0.5, ext)
                r1 += 1
                var_scale += 1

        for (id, p) in self.encoder.rand_vars:
            if p == -1:
                write_rand_var(f, id, 0.5, ext)
                var_scale += 1
            else:
                write_rand_var(f, id, p, ext)
            r1 += 1
        # print('Scale for sel vars = 2^', scale, ', ', 2**scale)

        e1 = 0

        for id in evid_vars:
            write_exist_var(f, id, ext)
            e1 += 1

        print('Total Scale = 2^', var_scale, ', ', 2**(var_scale))

        for id in self.encoder.intro_vars:
            write_exist_var(f, id, ext)
            e1 += 1

        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')
        f.close()

        print('(var, cls, r, e) = (%d, %d, %d, %d)' % (var_num, clause_num, r1, e1))
        print('---------------------')

    def write_wcnf(self, filename):  # weighted model counting
        name, ext = os.path.splitext(filename)
        if ext != '.wcnf':
            raise ValueError('Unknown extension %s' % (ext))

        print('Filename =', filename)

        f = open(filename, 'w')
        var_num = len(self.encoder.state_vars) + \
            len(self.encoder.rand_vars) + len(self.encoder.intro_vars) + 0
        clause_num = len(self.encoder.clauses)

        # header
        f.write('p cnf %d %d\n' % (var_num, clause_num))

        # clauses
        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')

        r1 = 0
        scale = 0
        for (id, p) in self.encoder.rand_vars:
            if p == -1:
                f.write('w %d -1\n' % (id))
                # scale += 1
            else:
                f.write('w %d %f\n' % (id, p))
                r1 += 1

        # print('Scale for sel vars = 2^', scale, ', ', 2**scale)

        evid_vars = []
        for (node_id, state) in self.net.evids:
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2:
                if abs(vars[0]) == abs(vars[1]):
                    evid_vars.append(vars[1])
                else:
                    evid_vars += vars
            else:
                evid_vars += vars

        var_scale = 0 + scale
        for id in self.encoder.state_vars:
            if id not in evid_vars:
                f.write('w %d -1\n' % (id))
                r1 += 1
                # var_scale += 1

        e1 = 0
        for id in evid_vars:
            f.write('w %d -1\n' % (id))
            e1 += 1

        print('Total Scale = 2^', var_scale, ', ', 2**var_scale)

        for id in self.encoder.intro_vars:
            f.write('w %d -1\n' % (id))
            e1 += 1

        f.close()

        print('(var, cls, r, e) = (%d, %d, %d, %d)' % (var_num, clause_num, r1, e1))
        print('---------------------')

    def write_cnf(self, filename):  # (projected) model counting
        name, ext = os.path.splitext(filename)
        if ext != '.cnf':
            raise ValueError('Unknown extension %s' % (ext))

        print('Filename =', filename)

        f = open(filename, 'w')
        f.write('c ind ')

        r1 = 0
        scale = 0
        for (id, p) in self.encoder.rand_vars:
            assert (p == -1) or (p == 0.5)
            f.write('%d ' % id)
            r1 += 1
            if p == -1:
                scale += 1

        # print('Scale for sel vars = 2^', scale, ', ', 2**scale)

        evid_vars = []
        for (node_id, state) in self.net.evids:
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2:
                if abs(vars[0]) == abs(vars[1]):
                    evid_vars.append(vars[1])
                else:
                    evid_vars += vars
            else:
                evid_vars += vars

        var_scale = 0 + scale
        for id in self.encoder.state_vars:
            if id not in evid_vars:
                f.write('%d ' % (id))
                var_scale += 1
                r1 += 1
        f.write('0\n')

        print('Total Scale = 2^', var_scale, ', ', 2**var_scale)

        var_num = len(self.encoder.state_vars) + \
            len(self.encoder.rand_vars) + len(self.encoder.intro_vars) + 0
        clause_num = len(self.encoder.clauses)

        # header
        f.write('p cnf %d %d\n' % (var_num, clause_num))

        # clauses
        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')

        f.close()

        e1 = var_num - r1
        print('(var, cls, r, e) = (%d, %d, %d, %d)' % (var_num, clause_num, r1, e1))
        print('---------------------')

    def write_mc2021(self, filename):
        name, ext = os.path.splitext(filename)
        if ext != '.mc2021':
            raise ValueError('Unknown extension %s' % (ext))

        print('Filename =', filename)

        f = open(filename, 'w')
        var_num = len(self.encoder.state_vars) + \
            len(self.encoder.rand_vars) + len(self.encoder.intro_vars) + 0
        clause_num = len(self.encoder.clauses)

        # header
        f.write('p cnf %d %d\n' % (var_num, clause_num))
        f.write('c t wmc\n')

        r1 = 0
        scale = 0
        for (id, p) in self.encoder.rand_vars:
            if p == -1:
                # f.write('c p %d -1\n' % (id))
                # scale += 1
                pass
            else:
                f.write('c p weight %d %f 0\n' % (id, p))
            r1 += 1

        # print('Scale for sel vars = 2^', scale, ', ', 2**scale)

        evid_vars = []
        for (node_id, state) in self.net.evids:
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2:
                if abs(vars[0]) == abs(vars[1]):
                    evid_vars.append(vars[1])
                else:
                    evid_vars += vars
            else:
                evid_vars += vars

        var_scale = 0 + scale
        for id in self.encoder.state_vars:
            if id not in evid_vars:
                # f.write('w %d 0.5\n' % (id))
                r1 += 1
                # var_scale += 1

        e1 = 0
        for id in evid_vars:
            # f.write('c p %d -1\n' % (id))
            e1 += 1

        print('Total Scale = 2^', var_scale, ', ', 2**var_scale)

        for id in self.encoder.intro_vars:
            # f.write('c p %d -1\n' % (id))
            e1 += 1

        # clauses
        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')

        f.close()

        print('(var, cls, r, e) = (%d, %d, %d, %d)' % (var_num, clause_num, r1, e1))
        print('---------------------')

    def write_ssat_mpe_er(self, filename):
        name, ext = os.path.splitext(filename)
        if ext != '.ssat' and ext != '.sdimacs':
            raise ValueError('Unknown extension %s' % (ext))

        print('Filename =', filename)

        f = open(filename, 'w')
        var_num = len(self.encoder.state_vars) + \
            len(self.encoder.rand_vars) + len(self.encoder.intro_vars)
        clause_num = len(self.encoder.clauses)

        if ext == '.ssat':
            f.write('%d\n' % (var_num))
            f.write('%d\n' % (clause_num))
        elif ext == '.sdimacs':
            f.write('p cnf %d %d\n' % (var_num, clause_num))

        evid_vars = []
        for (node_id, state) in self.net.evids:
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2 and not self.encoder.log_state:
                evid_vars.append(vars[1])
            else:
                evid_vars += vars

        e1 = 0
        for id in self.encoder.state_vars:
            if id not in evid_vars:
                write_exist_var(f, id, ext)
                e1 += 1

        r1 = 0
        scale = 0
        for (id, p) in self.encoder.rand_vars:
            if p == -1:
                write_rand_var(f, id, 0.5, ext)
                scale += 1
            else:
                write_rand_var(f, id, p, ext)
            r1 += 1
        print('Scale for state vars = 2^', scale, ', ', 2**scale)

        for id in evid_vars:
            write_exist_var(f, id, ext)
            e1 += 1

        e2 = 0
        for id in self.encoder.intro_vars:
            write_exist_var(f, id, ext)
            e2 += 1

        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')
        f.close()

        print('(var, cls, e1, r, e2) = (%d, %d, %d, %d, %d)' % (var_num, clause_num, e1, r1, e2))
        print('---------------------')

    def write_ssat_map_er(self, filename):
        name, ext = os.path.splitext(filename)
        if ext != '.ssat' and ext != '.sdimacs':
            raise ValueError('Unknown extension %s' % (ext))

        print('Filename =', filename)

        # collect information
        var_num = len(self.encoder.state_vars) + \
            len(self.encoder.rand_vars) + len(self.encoder.intro_vars)
        clause_num = len(self.encoder.clauses)

        # evidence
        evid_vars = []
        for (node_id, state) in self.net.evids:
            if node_id in self.net.query_var:
                continue
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2 and not self.encoder.log_state:
                evid_vars.append(vars[1])
            else:
                evid_vars += vars

        # map
        map_vars = []
        for node_id in self.net.query_var:
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2 and not self.encoder.log_state:
                map_vars.append(vars[1])
            else:
                map_vars += vars

        # write file
        f = open(filename, 'w')

        if ext == '.ssat':
            f.write('%d\n' % (var_num))
            f.write('%d\n' % (clause_num))
        elif ext == '.sdimacs':
            f.write('p cnf %d %d\n' % (var_num, clause_num))

        # first exist
        e1 = 0
        for id in map_vars:
            write_exist_var(f, id, ext)
            e1 += 1

        # random
        r1 = 0
        scale = 0

        # states
        for id in self.encoder.state_vars:
            if id not in evid_vars and id not in map_vars:
                write_rand_var(f, id, 0.5, ext)
                scale += 1
                r1 += 1

        # probability
        for (id, p) in self.encoder.rand_vars:
            if p == -1:
                write_rand_var(f, id, 0.5, ext)
                scale += 1
            else:
                write_rand_var(f, id, p, ext)
            r1 += 1

        print('Scale for state vars = 2^', scale, ', ', 2**scale)

        # second exist
        e2 = 0
        for id in evid_vars:
            write_exist_var(f, id, ext)
            e2 += 1

        for id in self.encoder.intro_vars:
            write_exist_var(f, id, ext)
            e2 += 1

        # clauses
        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')
        f.close()

        print('(var, cls, e1, r, e2) = (%d, %d, %d, %d, %d)' % (var_num, clause_num, e1, r1, e2))
        print('---------------------')

    def write_ssat_sdp_rer(self, filename):
        name, ext = os.path.splitext(filename)
        if ext != '.ssat' and ext != '.sdimacs':
            raise ValueError('Unknown extension %s' % (ext))

        print('Filename =', filename)

        # variable order
        # self.net.nodes.sort(key=lambda n: len(n.cpt)*len(n.cpt[0]))

        # collect information
        var_num = len(self.encoder.state_vars) + \
            len(self.encoder.rand_vars) + len(self.encoder.intro_vars) + 1
        clause_num = len(self.encoder.clauses)

        # evidence
        evid_vars = []
        for (node_id, state) in self.net.evids:
            if not self.net.id2node[node_id].cared:
                continue
            vars = self.encoder.node_id2state_vars[node_id]
            if len(vars) == 2 and not self.encoder.log_state:
                evid_vars.append(vars[1])
            else:
                evid_vars += vars

        # unobserved
        unobserved_vars = []
        for n in self.net.nodes:    # topological order
            if not n.depend:
                continue
            node_id = n.id
            if node_id in self.net.unobserved:
                vars = self.encoder.node_id2state_vars[node_id]
                if len(vars) == 2 and not self.encoder.log_state:
                    unobserved_vars.append(vars[1])
                else:
                    unobserved_vars += vars

        # write file
        f = open(filename, 'w')

        if ext == '.ssat':
            f.write('%d\n' % (var_num))
            f.write('%d\n' % (clause_num))
        elif ext == '.sdimacs':
            f.write('p cnf %d %d\n' % (var_num, clause_num))

        scale = 0
        # first random
        r1 = 0
        for id in unobserved_vars:
            write_rand_var(f, id, 0.5, ext, True)
            scale += 1
            r1 += 1

        e1 = 1
        write_thr_var(f, self.encoder.thr_var, self.net.dec_thr, ext)

        # random
        r2 = 0

        # states
        # for id in self.encoder.state_vars:
        for n in self.net.nodes:    # topological order
            if not n.depend:
                continue
            for id in self.encoder.node_id2state_vars[n.id]:
                if id not in unobserved_vars and id not in evid_vars:
                    write_rand_var(f, id, 0.5, ext, True)
                    scale += 1
                    r2 += 1

        # probability
        for (id, p) in self.encoder.rand_vars:
            if p == -1:
                write_rand_var(f, id, 0.5, ext)
                scale += 1
            else:
                write_rand_var(f, id, p, ext)
            r2 += 1

        print('Scale for state vars = 2^', scale, ', ', 2**scale)

        # second exist
        e2 = 0
        for id in evid_vars:
            write_exist_var(f, id, ext)
            e2 += 1

        for id in self.encoder.intro_vars:
            write_exist_var(f, id, ext)
            e2 += 1

        # clauses
        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')
        f.close()

        print('(var, cls, r1, e1, r2, e2) = (%d, %d, %d, %d, %d, %d)' %
              (var_num, clause_num, r1, e1, r2, e2))
        print('---------------------')

    def write_ssat_id(self, filename):
        name, ext = os.path.splitext(filename)
        if ext != '.ssat' and ext != '.sdimacs':
            raise ValueError('Unknown extension %s' % (ext))

        f = open(filename, 'w')
        var_num = len(self.encoder.state_vars) + len(self.encoder.rand_vars)
        var_num += len(self.encoder.intro_vars)
        var_num += len(self.encoder.dec_vars) + len(self.encoder.ob_vars)
        var_num += len(self.encoder.util_vars) + len(self.encoder.util_state_vars)
        if self.encoder.log_state and not self.encoder.causal:
            var_num -= len(self.encoder.ob_vars)
        clause_num = len(self.encoder.clauses)

        if ext == '.ssat':
            f.write('%d\n' % (var_num))
            f.write('%d\n' % (clause_num))
        elif ext == '.sdimacs':
            f.write('p cnf %d %d\n' % (var_num, clause_num))

        ssat_level = 0
        var_num_l = []
        all_ob_vars = []
        # decisions
        for level in range(self.net.max_dec_level):
            l = self.net.max_dec_level - level
            nodes = self.net.level2dec[l][::-1]  # topological order
            d_cnt = 0
            o_cnt = 0
            dec_vars = []
            ob_vars = []
            for n in nodes:
                dec_vars += self.encoder.node_id2dec_vars[n.id]
                ob_vars += self.encoder.node_id2ob_vars[n.id]
            for (id, p) in ob_vars:
                o_cnt += 1
                write_rand_var(f, id, p, ext)
            for id in dec_vars:
                d_cnt += 1
                write_exist_var(f, id, ext)
            if o_cnt > 0:
                var_num_l.append(o_cnt)
                ssat_level += 1
            var_num_l.append(d_cnt)
            ssat_level += 1
            for (v, p) in ob_vars:
                all_ob_vars.append(v)

        num_r = 0
        scale = 0
        for id in self.encoder.state_vars:
            if id not in all_ob_vars:
                scale += 1
                num_r += 1
                write_rand_var(f, id, 0.5, ext)

        for id in self.encoder.util_state_vars:
            scale += 1
            num_r += 1
            write_rand_var(f, id, 0.5, ext)

        print('Scale for state vars = 2^', scale)

        for (id, p) in self.encoder.util_vars:
            num_r += 1
            write_rand_var(f, id, p, ext)

        for (id, p) in self.encoder.rand_vars:
            num_r += 1
            write_rand_var(f, id, p, ext)

        num_e = 0
        for id in self.encoder.intro_vars:
            num_e += 1
            write_exist_var(f, id, ext)

        for cl in self.encoder.clauses:
            for id in cl:
                f.write('%d ' % (id))
            f.write('0\n')
        f.close()

        var_num_l.append(num_r)
        var_num_l.append(num_e)
        ssat_level += 2

        print('(var, cls) = (%d, %d)' % (var_num, clause_num))
        print('(level, per level) = (%d, %s)' % (ssat_level, var_num_l))


def write_exist_var(f, id, ext):
    if ext == '.ssat':
        f.write('%d x%d E\n' % (id, id))
    elif ext == '.sdimacs':
        f.write('e %d 0\n' % (id))


def write_rand_var(f, id, p, ext, state=False):
    if ext == '.ssat':
        f.write('%d x%d R %s\n' % (id, id, str(p)))
    elif ext == '.sdimacs':
        f.write('r %s %d 0\n' % (str(p), id))


def write_thr_var(f, id, thr, ext):
    if ext == '.ssat':
        f.write('%d x%d T %f\n' % (id, id, thr))
    elif ext == '.sdimacs':
        f.write('t %f %d 0\n' % (thr, id))
