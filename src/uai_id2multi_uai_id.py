import os
import sys

from PGM import Network


def main(argv):
    infile = argv[1]
    outfile = infile.replace('.limid', '.uai')

    net = Network(kind='ID', query='MEU')
    net.read(infile)
    net.write_uai_id(outfile)


if __name__ == "__main__":
    main(sys.argv)
