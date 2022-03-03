import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.uai.log'))
    ssat_files = glob.glob(os.path.join(dirname, '*.ssat.log'))
    samiam_files = glob.glob(os.path.join(dirname, '*.samiam.log'))

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name] = [None]*14
        # summary[name][:8] = list(parse_sdp_transform_log(filename))

    '''
    DCSSAT Runtime log
    '''
    for filename in ssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name][8:11] = list(parse_ssat_log(filename))

    '''
    SamIam SDP Runtime log
    '''
    for filename in samiam_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name][11:] = list(parse_samiam_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Scale', 'Prob', '#v', '#cls', '#entry', 'Trans Time',
                         'DCSSAT Time', 'SDP', 'SamIam Time'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            scale, num_vars, num_cls, transtime, memory, useful, num_cc, num_entry, runtime, memory, prob, sdp, t2, mem = summary[
                name]
            writer.writerow([name, scale, prob, num_vars, num_cls,
                             num_entry, transtime, runtime, sdp, t2])


if __name__ == "__main__":
    main(sys.argv)
