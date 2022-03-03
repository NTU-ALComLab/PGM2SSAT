import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*_prune.uai'))
    wmbmm_files = glob.glob(os.path.join(dirname, '*_prune.uai.st_wmbmm_tw.log'))
    gdd_files = glob.glob(os.path.join(dirname, '*_prune.uai.st_gdd_bw.log'))

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0].replace('_prune', '')
        # print('Collecting summary:', name)
        summary[name] = [None]*6
        # summary[name][:7] = list(parse_id_transform_log(filename))

    '''
    wmbmm Runtime log
    '''
    for filename in wmbmm_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0].replace('_prune', '')
        # print('Collecting answer:', name)
        summary[name][:3] = list(parse_st_log(filename))

    '''
    gdd Runtime log
    '''
    for filename in gdd_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0].replace('_prune', '')
        # print('Collecting answer:', name)
        summary[name][3:6] = list(parse_st_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'wmbmm Time', 'wmbmm Mem',
                         'wmbmm ub', 'gdd Time', 'gdd Mem', 'gdd ub'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            wmbmmtime, wmbmmmem, wmbmmub, gddtime, gddmem, gddub = summary[name]
            writer.writerow([name, wmbmmtime, wmbmmmem, wmbmmub, gddtime, gddmem, gddub])


if __name__ == "__main__":
    main(sys.argv)
