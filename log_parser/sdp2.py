import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.uai.log'))
    cachet_files = glob.glob(os.path.join(dirname, '*.cachet.log'))
    ssat_files = glob.glob(os.path.join(dirname, '*.ssat.log'))

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name] = [None]*11
        summary[name][:6] = list(parse_sdp_transform_log(filename))

    '''
    DCSSAT Runtime log
    '''
    for filename in ssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name][6:9] = list(parse_ssat_log(filename))

    '''
    Cachet Runtime log
    '''
    for filename in cachet_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name][9:] = list(parse_cachet_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Transtime', 'Transmem', 'useful', 'Scale', 'Prob', '#v', '#cls',
                         'DCSSAT Time', 'DCSSAT Mem', 'Evid Prob', 'Cachet Time'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            scale, num_vars, num_cls, transtime, transmem, useful, runtime, mem, prob, cachet_time, evid_prob = summary[
                name]
            writer.writerow([name, transtime, transmem, useful, scale, prob, num_vars,
                             num_cls, runtime, mem, evid_prob, cachet_time])


if __name__ == "__main__":
    main(sys.argv)
