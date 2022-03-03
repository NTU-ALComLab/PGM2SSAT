import os
import sys
import datetime
from pathlib import Path
from pysdd.sdd import SddManager, Vtree, WmcManager, SddNode


def main(argv):
    ssat_file = argv[1]
    # here = Path(__file__).parent.parent
    vtree_file = Path(ssat_file.replace('.ssat', '.vtree'))
    sdd_file = Path(ssat_file.replace('.ssat', '.sdd'))

    num_vars, h_vars, tmp_file = read_sdpssat(ssat_file)

    # give X_vars
    x_var = [0 for i in range(num_vars+1)]
    for v in h_vars:
        x_var[v] = 1

    # construct vtree
    vtree = Vtree(var_count=num_vars, is_X_var=x_var)

    # convert cnf to sdd
    sdd = SddManager.from_vtree(vtree)
    root = sdd.read_cnf_file(bytes(Path(tmp_file)))
    print('Save %s' % sdd_file)
    root.save(bytes(sdd_file))
    print('Save %s' % vtree_file)
    root.vtree().save(bytes(vtree_file))

    os.system('rm %s' % tmp_file)


def read_sdpssat(filename):
    print('Read %s' % filename)
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    num_vars = int(lines[0].strip())
    num_cls = int(lines[1].strip())
    h_vars = []
    h_flag = True
    for i in range(num_vars):
        pars = lines[i+2].strip().split(' ')
        if pars[2] == 'R' and h_flag:
            id = int(pars[0])
            h_vars.append(id)
        elif pars[2] == 'T':
            s_var = int(pars[0])
            h_flag = False
        elif pars[2] == 'R' and not h_flag:
            id = int(pars[0])
        elif pars[2] == 'E':
            id = int(pars[0])

    stamp = str(os.getpid()) + '-' + str(datetime.datetime.now().timestamp())
    tmp_file = 'tmp-%s.cnf' % stamp
    f = open(tmp_file, 'w')
    f.write('p cnf %d %d\n' % (num_vars, num_cls-1))
    for i in range(num_cls-1):
        f.write(lines[2+num_vars+i])
    f.close()

    return num_vars, h_vars, tmp_file


if __name__ == "__main__":
    main(sys.argv)
