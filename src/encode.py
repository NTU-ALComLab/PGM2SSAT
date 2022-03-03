from math import inf
import os
import sys
import argparse

from PGM import Network
from ssat_encoder import SSATEncoder
from ssat_writer import SSATWriter, write_exist_var


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, required=True)
    # parser.add_argument('-o', '--output', type=str)
    parser.add_argument('-e', '--evid_file', type=str, default='')
    parser.add_argument('-n', '--net_type', type=str,
                        choices=['CPT', 'BN', 'ID', 'CG'], required=True)
    parser.add_argument('-q', '--query', type=str,
                        choices=['PE', 'MPE', 'MAP', 'SDP', 'MEU'], default='PE',
                        help='PE, MPE, MAP, SDP for Bayesian network; MEU for influence diagram')
    parser.add_argument('-qf', '--query_file', type=str, default='')
    parser.add_argument('-m', '--method', type=str, choices=[
                        'bklm16', 'sbk05', 'val', 'share_bit', 'direct_bit', 'bit_sop', 'bit_aig', 'all05'], required=True)
    parser.add_argument('-p', '--prune', default=False, action='store_true',
                        help='Prune network by evidence')
    parser.add_argument('-o', '--opt', type=str, choices=['none', 'qm', 'esp'],
                        default='none', help='quine-mccluskey or espresso minimization')
    parser.add_argument('-c', '--share_across_table', default=False, action='store_true')
    parser.add_argument('-s', '--state', type=str, default='log', choices=['linear', 'log'])
    parser.add_argument('-b', '--bit', type=int, default=32,
                        help='Number of bits when using bit sharing methods')
    parser.add_argument('-cc', '--connected_component', default=False, action='store_true')
    args = parser.parse_args()

    print(args)

    infile = args.input
    net_type = args.net_type
    print('Processing', infile)

    name, ext = os.path.splitext(infile)
    outfile1 = infile.replace(ext, '.sdimacs')
    outfile2 = infile.replace(ext, '.ssat')
    outfile3 = infile.replace(ext, '.wcnf')
    outfile4 = infile.replace(ext, '.cnf')  # for approxmc
    # outfile5 = infile.replace(ext, '.mc2021')

    if args.net_type == 'BN':
        net = Network(kind='BN', query=args.query)
    elif args.net_type == 'ID':
        net = Network(kind='ID', query='MEU')
    elif args.net_type == 'CG':
        net = Network(kind='ID', query='MEU', causal=True)
    elif args.net_type == 'CPT':
        net = Network(kind='CPT', query='PE')

    net.read(infile, args.evid_file, args.query_file)

    # entry = net.cal_num_entry()
    # print('Total entry = ', entry)

    encoder = SSATEncoder(net, args.method, args.query, num_bit=args.bit,
                          log_state=(args.state == 'log'), prune=args.prune,
                          connected_component=args.connected_component,
                          opt=args.opt, share_val=args.share_across_table)
    encoder.tossat()

    writer = SSATWriter(encoder)
    writer.write_ssat(outfile1)
    writer.write_ssat(outfile2)
    if args.net_type == 'BN' and args.query == 'PE':
        writer.write_wcnf(outfile3)
        if args.method == 'all05':
            writer.write_cnf(outfile4)
        # writer.write_mc2021(outfile5)

    '''
    PE query needed for SDP
    '''
    # if args.query == 'SDP':
    #     encoder.reset()
    #     encoder.query = 'PE'
    #     encoder.tossat()
    #     writer.write_wcnf(outfile3)


if __name__ == "__main__":
    main()
