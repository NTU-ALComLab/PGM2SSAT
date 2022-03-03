import sys
import os

from PGM import Network


def main(argv):
    filename = argv[1]
    name, ext = os.path.splitext(filename)
    evid_file = filename + '.evid'
    map_file = filename + '.map'

    net = Network(kind='BN', query='MAP')
    net.read(filename)
    net.write_evidence(evid_file, 'single_line')
    net.write_map_query(map_file, 'single_line')


if __name__ == "__main__":
    main(sys.argv)
