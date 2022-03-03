import os
import sys

from PGM import Network
from ssat_encoder import SSATEncoder
from ssat_writer import SSATWriter


def main(argv):
    infile = argv[2]
    net_type = argv[1]
    print('Processing', infile)

    name, ext = os.path.splitext(infile)
    outfile = infile + '.evid'
    if net_type == 'bn':
        net = Network(kind='BN', query='MPE')
    elif net_type == 'id':
        net = Network(kind='ID', query='MEU')
    elif net_type == 'cg':
        net = Network(kind='ID', query='MEU', causal=True)
    net.read(infile)
    net.gen_evid(5)
    net.write_evidence(outfile)
    print('Generate evidence to ', outfile)


if __name__ == "__main__":
    main(sys.argv)
