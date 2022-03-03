import os
import sys

from PGM import Network
from ssat_encoder import SSATEncoder
from ssat_writer import SSATWriter


def main(argv):
    infile = argv[1]
    print('Processing', infile)

    name, ext = os.path.splitext(infile)
    head, tail = os.path.split(infile)
    outfile = head + '/' + 'ID_' + tail.replace(ext, '.uai')

    net = Network(kind='BN', query='MPE')
    net.read(infile)
    net.bn2id(8, 2, 3)
    net.write_uai_id(outfile)
    print('Generate ID to ', outfile)


if __name__ == "__main__":
    main(sys.argv)
