import os
import sys

from PGM import Network


def main(argv):
    infile = argv[1]
    kind = argv[2]
    query = argv[3]

    outfile = infile.replace('.limid', '_prune.limid')

    net = Network(kind=kind, query=query)
    net.read(infile)

    '''
    prune nodes with query
    '''
    print('Total number of nodes = ', net.num_nodes)
    net.mark_redundent()
    print('Pruned number of nodes = ', net.count_depend())
    if query == 'SDP':
        net.mark_redundent(enable_d=True)
        print('Pruned (with d) number of nodes = ', net.count_depend())
    net.nodes = [n for n in net.nodes if n.depend]

    entry = net.cal_num_entry()
    print('Total entry = ', entry)

    if query == 'SDP':
        num_components = net.find_connected_components()
        print('Number of connected components = ', num_components)
        net.collect_cared_nodes()
        print('Pruned number of nodes connected = ', net.count_depend())

    '''
    relabel the id of nodes
    '''
    net.relabel_nodes()

    net.write(outfile)


if __name__ == "__main__":
    main(sys.argv)
