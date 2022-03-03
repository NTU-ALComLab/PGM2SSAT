import os
import sys

# from PGM import Network


def main(argv):
    infile = argv[1]
    # outfile = infile.replace('.bif', '.uai')

    # net = Network(kind='ID', query='MEU')
    # net.read(infile)
    # net.write_uai_id_multi(infile)
    f = open(infile, 'r')
    lines = f.readlines()
    import pdb
    pdb.set_trace()


if __name__ == "__main__":
    main(sys.argv)
