import os
import sys

from PGM import Network
from ssat_encoder import SSATEncoder
from ssat_writer import SSATWriter


def main(argv):
    infile = argv[1]
    print('Processing', infile)

    name, ext = os.path.splitext(infile)
    evid_file = infile + '.evid'
    map_file = infile + '.map'
    net = Network(kind='BN', query='PE')
    net.read(infile)
    num_cared = 30
    num_evids = 0
    net.gen_map(num_cared, num_evids)
    net.write_evidence(evid_file)
    net.write_map_query(map_file)
    print('Generate map query to %s with %d cared, to %s with %d evidence' %
          (map_file, num_cared, evid_file, num_evids))


if __name__ == "__main__":
    main(sys.argv)
