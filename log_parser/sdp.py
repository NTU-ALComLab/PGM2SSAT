import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.uai'))
    samiam_files = glob.glob(os.path.join(dirname, '*.uai.samiam.log'))
    sdd_files = glob.glob(os.path.join(dirname, '*.ssat.sdd.log'))
    ssat_files = glob.glob(os.path.join(dirname, '*.ssat.ssat-hue.log'))

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name] = [None]*9

    '''
    SamIam SDP Runtime log
    '''
    for filename in samiam_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name][:3] = list(parse_samiam_log(filename))

    '''
    SDD log
    '''
    for filename in sdd_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name][3:6] = list(parse_sdd_log(filename))

    '''
    DCSSAT Runtime log
    '''
    for filename in ssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name][6:] = list(parse_ssat_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'SDP', 'SamIam', 'SamIam Mem', 'SDD done', 'SDD',
                         'SDD Mem', 'Prob', 'DCSSAT', 'DCSSAT Mem'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            sdp, samiam, samiam_mem, finished, sdd, sdd_mem, dcssat, dc_mem, prob = summary[name]
            writer.writerow([name, sdp, samiam, samiam_mem, finished,
                             sdd, sdd_mem,  prob, dcssat, dc_mem])


if __name__ == "__main__":
    main(sys.argv)
