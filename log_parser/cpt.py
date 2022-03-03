import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.cpt.log'))
    ssat_files = glob.glob(os.path.join(dirname, '*.ssat-heu.log'))
    sdimacs_files = glob.glob(os.path.join(dirname, '*.sdimacs.log'))
    claussat_files = glob.glob(os.path.join(dirname, '*.claussat.log'))
    sharpssat_files = glob.glob(os.path.join(dirname, '*.sharpssat-no-mem.log'))

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        if '_prune' in name:
            continue
        summary[name] = [None]*17
        summary[name][:5] = list(parse_cpt_transform_log(filename))

    '''
    DCSSAT Runtime log
    '''
    for filename in ssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        if '_prune' in name:
            continue
        # print('Collecting answer:', name)
        summary[name][5:8] = list(parse_ssat_log(filename))

    '''
    erSSAT Runtime log
    '''
    for filename in sdimacs_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        if '_prune' in name:
            continue
        # print('Collecting answer:', name)
        summary[name][8:11] = list(parse_ssatabc_log(filename))

    '''
    ClauSSat Runtime log
    '''
    for filename in claussat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        if '_prune' in name:
            continue
        # print('Collecting answer:', name)
        summary[name][11:14] = list(parse_claussat_log(filename))

    '''
    sharpSAT runtime log
    '''
    for filename in sharpssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        if '_prune' in name:
            continue
        # print('Collecting answer:', name)
        summary[name][14:] = list(parse_sharpssat_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Scale', 'Prob', '#v', '#cls', 'Trans Time',
                         'DCSSAT Time', 'DCSSAT Mem', 'erssat Time', 'erssat Mem', 'erssat prob',
                         'Claussat Time', 'Claussat Mem', 'Claussat prob', 'sharp time', 'sharp mem', 'sharp prob'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            scale, num_vars, num_cls, transtime, transmem, runtime, memory, prob, er_time, er_mem, er_prob, clau_time, clau_mem, clau_prob, sharp_time, sharp_mem, sharp_prob = summary[
                name]
            writer.writerow([name, scale, prob, num_vars, num_cls,
                             transtime, runtime, memory, er_time, er_mem, er_prob, clau_time, clau_mem,
                             clau_prob, sharp_time, sharp_mem, sharp_prob])


if __name__ == "__main__":
    main(sys.argv)
