import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.uai.log'))
    sdd_files = glob.glob(os.path.join(dirname, '*.sdd.log'))

    summary = {}

    '''
    SSAT Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name] = [None]*3
        # summary[name][:5] = list(parse_sdp_transform_log(filename))

    '''
    Transform log
    '''
    for filename in sdd_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # name = name.split('.')[0].replace('-min', '')
        # print('Collecting summary:', name)
        summary[name] = list(parse_sdd_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'finished', 'time', 'mem'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            finished, runtime, mem = summary[name]
            writer.writerow([name, str(finished), runtime, mem])


if __name__ == "__main__":
    main(sys.argv)
