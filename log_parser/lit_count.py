import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.uai.log'))
    ssat_files = glob.glob(os.path.join(dirname, '*.ssat'))

    summary = {}

    '''
    SSAT Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name] = [None]
        # summary[name][:5] = list(parse_sdp_transform_log(filename))

    '''
    Transform log
    '''
    for filename in ssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # name = name.split('.')[0].replace('-min', '')
        # print('Collecting summary:', name)
        summary[name] = list(parse_ssat_lit(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'num_lits'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            num_lits, = summary[name]
            writer.writerow([name, num_lits])


if __name__ == "__main__":
    main(sys.argv)
