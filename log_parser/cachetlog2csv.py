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

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        summary[name] = list(parse_pe_transform_log(filename)) + [None, None]

    '''
    Cachet Runtime log
    '''
    for filename in cachet_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        runtime, prob = list(parse_cachet_log(filename))
        summary[name][3] = runtime
        summary[name][4] = prob

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Scale', 'Prob', '#v', '#cls', 'Time'])
        keys = list(summary.keys())
        keys.sort(key=lambda s: int(s.split('_')[-1]))
        for name in keys:
            scale, num_vars, num_cls, runtime, prob = summary[name]
            writer.writerow([name, scale, prob, num_vars, num_cls, runtime])


if __name__ == "__main__":
    main(sys.argv)
