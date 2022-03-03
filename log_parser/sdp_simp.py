import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.uai.log'))
    ssat_heu_files = glob.glob(os.path.join(dirname, '*.ssat-heu.log'))
    ssat_myheu_files = glob.glob(os.path.join(dirname, '*.ssat-myheu.log'))

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name] = [None]*10
        summary[name][:7] = list(parse_sdp_transform_log(filename))

    '''
    DCSSAT Runtime log (topo heu)
    '''
    for filename in ssat_heu_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0].replace('-min', '')
        # print('Collecting answer:', name)
        summary[name][7:] = list(parse_ssat_log(filename))

    # '''
    # DCSSAT Runtime log (topo+moms heu)
    # '''
    # for filename in ssat_myheu_files:
    #     head, tail = os.path.split(filename)
    #     name, ext = os.path.splitext(tail)
    #     name = name.split('.')[0]
    #     # print('Collecting answer:', name)
    #     summary[name][9:] = list(parse_ssat_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Transtime', 'Transmem', 'useful', 'Connected components', 'Scale', '#v', '#cls',
                         'prob', 'time', 'mem'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            scale, num_vars, num_cls, transtime, transmem, useful, num_cc, runtime1, memory1, prob1 = summary[
                name]
            writer.writerow([name, transtime, transmem, useful, num_cc, scale, num_vars,
                             num_cls,  prob1, runtime1, memory1])


if __name__ == "__main__":
    main(sys.argv)
