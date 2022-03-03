import os
import sys

from PGM import Network
from ssat_encoder import SSATEncoder
from ssat_writer import SSATWriter


def main(argv):
    infile = argv[1]
    print('Processing', infile)

    name, ext = os.path.splitext(infile)
    outfile = infile + '.sdp'
    net = Network(kind='BN', query='SDP')
    net.read(infile)
    num_dec = 1
    num_unobserved = 1
    num_evids = 0
    net.gen_sdp(num_dec, num_unobserved, num_evids)
    net.dec_thr = 0.2
    net.write_sdp_query(outfile)
    print('Generate sdp query to %s with %d dec, %d unobserved, %d evidence' %
          (outfile, num_dec, num_unobserved, num_evids))


if __name__ == "__main__":
    main(sys.argv)
