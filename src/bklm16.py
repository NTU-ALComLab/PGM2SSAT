import os
import sys
import json


def main(argv):
    infile = argv[1]
    outfile = infile.replace('.uai', '.cnf')
    evid_file = infile + '.evid'

    cmd = './bn2cnf_linux -i %s -o tmp.cnf -w tmp.cnf.weight -v tmp.cnf.var -e LOG -s prime' % infile
    os.system(cmd)

    var_map = parse_var_file('tmp.cnf.var')

    evid_cl = None
    if os.path.isfile(evid_file):
        print('Find evidence file', evid_file)
        evid_cl = map_evid(evid_file, var_map)

    write_wcnf('tmp.cnf', 'tmp.cnf.weight', evid_cl, outfile)


def write_wcnf(cnf_file, weight_file, evid_cl, outfile):
    f = open(cnf_file, 'r')
    cnfs = f.readlines()
    pars = cnfs[0].strip().split()
    num_vars = int(pars[2])
    num_cls = int(pars[3])
    f.close()

    f = open(weight_file, 'r')
    weights = f.readlines()
    f.close()

    num_cls += len(evid_cl)

    f = open(outfile, 'w')
    f.write('p cnf %d %d\n' % (num_vars, num_cls))

    for line in cnfs[1:]:
        f.write(line)

    for cl in evid_cl:
        for v in cl:
            f.write('%d ' % v)
        f.write('0\n')

    # undefined = [1]*num_vars
    for line in weights:
        if line[0] == '-':
            continue
        elif line[0] == '0':
            continue
        else:
            f.write('w ')
            f.write(line)
            v = int(line.strip().split()[0])
            # undefined[v-1] = 0

    # for v, flag in enumerate(undefined):
    #     if flag == 0:
    #         f.write('w %d -1\n' % (v))

    f.close()


def map_evid(evid_file, var_map):
    f = open(evid_file, 'r')
    lines = f.readlines()
    f.close()

    num_evids = int(lines[1])

    evid_cl = []
    for i in range(num_evids):
        pars = lines[2+i].strip().split()
        id = int(pars[0])
        state = int(pars[1])
        s = var_map[id][state]
        for v in s:
            evid_cl.append([v])

    return evid_cl


def parse_var_file(var_file):
    f = open(var_file, 'r')
    lines = f.readlines()
    f.close()

    var_map = {}
    for line in lines:
        if len(line) > 0:
            pars = line.strip().split(' = ')

            id = int(pars[0])
            state_list = ''
            for i, s in enumerate(pars[1]):
                state_list += s
                if (i+1 < len(pars[1])) and (s == ']') and (pars[1][i+1] == '['):
                    state_list += ','
            states = json.loads(state_list)
            var_map[id] = states

    return var_map


if __name__ == "__main__":
    main(sys.argv)
