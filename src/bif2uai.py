import os
import sys

from PGM import Network


def main(argv):
    infile = argv[1]
    outfile = infile.replace('.bif', '.uai')

    net = Network(kind='BN', query='MPE')
    net.read(infile)
    net.write_uai_bn(outfile)


if __name__ == "__main__":
    main(sys.argv)
