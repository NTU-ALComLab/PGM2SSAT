import os
import sys
import datetime


def main(argv):
    ssat_file = argv[1]
    new_ssat_file = ssat_file.replace('.ssat', '-min.ssat')

    print('Read %s' % ssat_file)
    num_vars, num_cls, var_str, cls_str = read_ssat(ssat_file)

    stamp = str(os.getpid()) + '-' + str(datetime.datetime.now().timestamp())
    tmp_file = 'tmp-%s.cnf' % stamp
    tmp_out = 'tmp-%s-min.cnf' % stamp
    tmp_varmap = 'tmp-%s-min.varmap' % stamp

    # for negation of decision variables in SDP problem
    # cls_str = add_negation(cls_str)

    write_cnf(tmp_file, num_vars, num_cls, cls_str)

    cmd = './SatELite_v1.0_linux %s %s %s -' % (tmp_file, tmp_out, tmp_varmap)
    os.system(cmd)

    if os.path.isfile(tmp_out):
        new_num_vars, new_num_cls, new_cls_str = read_cnf(tmp_out)
        origin_num_vars, assignments, var_map = read_varmap(tmp_varmap)

        scale = cal_scale(var_str, assignments)
        print('Scale = ', scale)

        new_var_str = replace_ssat_vars(var_str, var_map)

        write_ssat(new_ssat_file, new_num_vars, new_num_cls, new_var_str, new_cls_str)
    else:
        write_ssat(new_ssat_file, 1, 1, '1 x1 R 0\n', '1 0\n')

    os.system('rm %s %s %s' % (tmp_file, tmp_out, tmp_varmap))


def read_ssat(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    num_vars = int(lines[0].strip())
    num_cls = int(lines[1].strip())

    var_str = lines[2:num_vars+2]
    cls_str = lines[num_vars+2:]

    return num_vars, num_cls, var_str, cls_str


def write_ssat(filename, num_vars, num_cls, var_str, cls_str):
    f = open(filename, 'w')
    f.write('%d\n' % num_vars)
    f.write('%d\n' % num_cls)
    for line in var_str:
        f.write(line)

    for line in cls_str:
        f.write(line)

    f.close()


def write_cnf(filename, num_vars, num_cls, cls_str):
    f = open(filename, 'w')
    f.write('p cnf %d %d\n' % (num_vars, num_cls))
    for cl in cls_str:
        f.write(cl)
    f.close()


def read_cnf(filename):
    f = open(filename)
    lines = f.readlines()
    f.close()

    num_vars = 0
    num_cls = 0
    cls_str = []
    for i, line in enumerate(lines):
        pars = line.strip().split()
        if len(pars) == 0:
            continue
        elif pars[0] == 'c':
            continue
        elif pars[0] == 'p':
            num_vars = int(pars[2])
            num_cls = int(pars[3])
            cls_str = lines[i+1:]
            break

    return num_vars, num_cls, cls_str


def read_varmap(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    origin_num_vars = int(lines[0].strip().split()[0])

    pars = lines[1].strip().split()
    assignments = [int(v) for v in pars[:-1]]

    pars = lines[2].strip().split()
    var_map = {}
    for i, v in enumerate(pars[:-1]):
        var_map[v] = str(i+1)

    return origin_num_vars, assignments, var_map


def replace_ssat_vars(var_str, var_map):
    new_var_str = []
    for line in var_str:
        pars = line.strip().split()
        id = pars[0]
        new_var = var_map.get(id)
        if new_var is None:
            continue

        new_line = '%s x%s ' % (new_var, new_var)
        new_line += pars[2] + ' ' + pars[3] + '\n'
        new_var_str.append(new_line)

    return new_var_str


def cal_scale(var_str, assignments):
    prob_map = {}
    for line in var_str:
        pars = line.strip().split()
        if pars[2] == 'R':
            prob_map[int(pars[0])] = float(pars[3])

    scale = 1
    for v in assignments:
        p = prob_map.get(abs(v))
        if p is not None:
            if v > 0:
                scale *= p
            else:
                scale *= (1-p)

    return scale


def add_negation(cls_str):
    cl = [int(v) for v in cls_str[-1].strip().split()]
    new_cl_str = ''
    for v in cl:
        new_cl_str += str(-v) + ' '
    new_cl_str += '\n'

    cls_str.append(new_cl_str)
    return cls_str


if __name__ == "__main__":
    main(sys.argv)
