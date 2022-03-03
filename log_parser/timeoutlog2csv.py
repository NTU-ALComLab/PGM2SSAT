import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'timeoutlog.csv')

    files = glob.glob(os.path.join(dirname, '*.samiam.log'))

    summary = {}

    '''
    Runtime log
    '''
    for filename in files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name] = list(parse_samiam_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'SDP', 'Time', 'Mem'])
        keys = list(summary.keys())
        keys.sort(key=lambda s: int(s.split('_')[-1]))
        for name in keys:
            sdp, runtime, memory = summary[name]
            writer.writerow([name, sdp, runtime, memory])


if __name__ == "__main__":
    main(sys.argv)
