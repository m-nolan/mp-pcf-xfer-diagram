import json
import numpy as np
import os
import pandas as pd

from argparse import ArgumentParser

def parse_args():
    parser = ArgumentParser(
        prog='generate_xfer_json.py',
        description='Creates a JSON file containing node, link information from MN CFB political committee/fund transfer data for a d3 force-directed graph.'
    )
    parser.add_argument('data_dir')
    parser.add_argument('-o','--output_dir',default=None)
    parser.add_argument('-m','--min_val',default=100000,type=int)
    args = parser.parse_args()
    if args.output_dir == None:
        args.output_dir = args.data_dir
    return args

def get_cfb_data(data_dir):
    pcf_table = pd.read_csv(os.path.join(data_dir,'PCF.csv'))
    xfer_table = pd.read_csv(os.path.join(data_dir,'PCFTransfers.csv'))
    return pcf_table, xfer_table

def clean_xfer_df(xfer_df):
    remove_row_idx = []
    xfer_df['TransferReverseSum'] = np.zeros(len(xfer_df))
    for idx, row in xfer_df.iterrows():
        if idx in remove_row_idx:   # don't double-count
            continue
        reverse_df = xfer_df[np.logical_and(xfer_df.source==row['target'],xfer_df.target==row['source'])]
        if len(reverse_df) > 0:
            remove_row_idx.append(*reverse_df.index.values)
            reverse_amount = reverse_df['value'].sum()
            xfer_df.loc[idx,'TransferReverseSum'] = reverse_amount
            xfer_df.loc[idx,'value'] -= reverse_amount
    return xfer_df.drop(remove_row_idx,axis=0)

def get_xfer_df(xfer_table,min_val):
    xfer_df = xfer_table.groupby(['PCFRegNumb','TransRegNumb'])[['TransAmt','TransferCashAmount','TransferInKindAmount']].sum()
    xfer_df['TransTotal'] = xfer_df.sum(axis=1)
    xfer_df = xfer_df.sort_values('TransTotal',ascending=False).reset_index()
    xfer_df.columns = ['source','target','TransAmt','TransferCashAmount','TransferInKindAmount','value']
    # subtract backflows, only doing arrows in one direction
    xfer_df = clean_xfer_df(xfer_df)
    return xfer_df[xfer_df.value > min_val]

def get_pcf_df(pcf_table,xfer_df):
    pcf_regnum_list = np.unique([xfer_df.source.values,xfer_df.target.values])
    return pcf_table[pcf_table.PCFRegNumb.isin(pcf_regnum_list)][['PCFRegNumb','Committee']]

def write_xfer_json(output_dir,pcf_df,xfer_df,min_val):
    d3_dict = {
        'nodes': [{'id': row.PCFRegNumb, 'name': row.Committee} for _, row in pcf_df.iterrows()], # row.name gives you the index value. Lesson learned.
        'links': [{'source': int(row.source), 'target': int(row.target), 'value': row.value} for _, row in xfer_df.iterrows()],
    }
    with open(os.path.join(output_dir,f'./xfer_data_{min_val}.json'),'w') as wf:
        wf.write(json.dumps(d3_dict))

def main():
    args = parse_args()
    pcf_table, xfer_table = get_cfb_data(args.data_dir)
    xfer_df = get_xfer_df(xfer_table,args.min_val)
    pcf_df = get_pcf_df(pcf_table,xfer_df)
    write_xfer_json(args.output_dir,pcf_df,xfer_df,args.min_val)

if __name__ == "__main__":
    main()