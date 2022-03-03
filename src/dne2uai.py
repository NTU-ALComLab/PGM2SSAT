import sys
import os

from PGM import Network


def main(argv):
    filename = argv[1]
    name, ext = os.path.splitext(filename)
    outfile = filename.replace(ext, '.uai')

    net = Network(kind='BN', query='PE')
    net.read(filename)
    net.write_uai_bn(outfile)


if __name__ == "__main__":
    main(sys.argv)
