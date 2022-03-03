import sys
import os


def main(argv):
    filename = argv[1]
    outfile = filename.replace('.erg', '.uai')

    evid_filename = filename + '.evid'
    use_evid = os.path.isfile(evid_filename)
    if use_evid:
        evid_outfile = outfile + '.evid'

    # read erg file
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    num_nodes = int(lines[0])

    # each node has how many states
    num_states = []
    pars = lines[1].strip().split()
    for n in pars:
        num_states.append(int(n))

    # each node has [incoming nodes]
    in_nodes = []
    for i in range(num_nodes):
        pars = lines[2+i].strip().split()
        n = int(pars[0])
        incoming = []
        for j in range(n):
            m = int(pars[j+1])
            incoming.append(m)
        in_nodes.append(incoming)

    f = open(outfile, 'w')
    f.write('BAYES\n')
    f.write(lines[0])
    f.write(lines[1])
    f.write(lines[0])
    for i in range(num_nodes):
        incoming = in_nodes[i]
        f.write('%d ' % (len(incoming)+1))
        for node in incoming:
            f.write('%d ' % (node))
        f.write('%d\n' % (i))

    for line in lines[2+num_nodes:]:
        if line[:4] == '/* P':
            continue
        elif line[:2] == '/*':
            break
        f.write(line)
    f.close()

    if use_evid:
        f = open(evid_filename, 'r')
        lines = f.readlines()
        f.close()
        f = open(evid_outfile, 'w')
        for line in lines:
            f.write(line)
        f.close()


if __name__ == "__main__":
    main(sys.argv)
