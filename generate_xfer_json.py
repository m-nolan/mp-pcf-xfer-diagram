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
    parser.add_argument('--filetype',choices=['json','csv'],default='json',type=str)
    parser.add_argument('-i','--ind',action='store_true',default=False)
    args = parser.parse_args()
    if args.output_dir == None:
        args.output_dir = args.data_dir
    return args

def get_cfb_data(data_dir):
    donor_table = pd.read_csv(os.path.join(data_dir,'PCFDonors.csv'))
    pcf_table = pd.read_csv(os.path.join(data_dir,'PCF.csv'))
    xfer_table = pd.read_csv(os.path.join(data_dir,'PCFTransfers.csv'))
    donor_table = donor_table.merge(pcf_table[['PCFRegNumb','Committee','Category']],how='left',on='PCFRegNumb')
    return donor_table, pcf_table, xfer_table

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
    return xfer_df[xfer_df.value >= min_val]

def get_noid_xfer_df(donor_table,min_val):
    nonind_xfer_df = donor_table[np.logical_and(donor_table.DonorRegNumb.isna(),donor_table.DonorType != 'I')].groupby(['DonorName','DonorType','Committee','Category','PCFRegNumb'])['DonationAmount'].sum().sort_values(ascending=False).reset_index()
    nonind_xfer_df.columns = ['DonorName','DonorType','Committee','Category','PCFRegNumb','value']
    ind_xfer_df = donor_table[np.logical_and(donor_table.DonorRegNumb.isna(),donor_table.DonorType == 'I')].groupby(['DonorName','Committee','Category','PCFRegNumb'])['DonationAmount'].sum().sort_values(ascending=False).reset_index()
    ind_xfer_df.columns = ['DonorName','Committee','Category','PCFRegNumb','value']
    return nonind_xfer_df[nonind_xfer_df.value >= min_val], ind_xfer_df[ind_xfer_df.value >= min_val]

def get_pcf_df(pcf_table,id_xfer_df,noid_nonind_xfer_df,noid_ind_xfer_df,ind_flag):
    pcf_regnum_list = [
            *id_xfer_df.source.values,
            *id_xfer_df.target.values,
            *noid_nonind_xfer_df.PCFRegNumb.values,
    ]
    if ind_flag:
        pcf_regnum_list.extend(noid_ind_xfer_df.PCFRegNumb.values)
    pcf_regnum_list = np.unique(pcf_regnum_list).astype(int)
    id_pcf_df = pcf_table[pcf_table.PCFRegNumb.isin(pcf_regnum_list)][['PCFRegNumb','Committee']]
    noid_nonind_df = pd.DataFrame(noid_nonind_xfer_df.DonorName.unique(),columns=['Committee'])
    noid_ind_df = pd.DataFrame(noid_ind_xfer_df.DonorName.unique(),columns=['Committee'])
    return id_pcf_df, noid_nonind_df, noid_ind_df

def collect_pcf_df(id_pcf_df,noid_nonind_pcf_df,noid_ind_pcf_df,ind_flag):
    id_pcf_df['Kind'] = 'T'
    noid_nonind_pcf_df['Kind'] = 'O'
    noid_ind_pcf_df['Kind'] = 'I'
    if ind_flag:
        noid_pcf_df = pd.concat([noid_nonind_pcf_df,noid_ind_pcf_df],ignore_index=True)
    else:
        noid_pcf_df = noid_nonind_pcf_df
    noid_pcf_df['PCFRegNumb'] = np.arange(len(noid_pcf_df))
    return pd.concat([id_pcf_df,noid_pcf_df],ignore_index=True)

def collect_xfer_df(id_xfer_df,noid_nonind_xfer_df,noid_ind_xfer_df,pcf_df,ind_flag):
    # add id to noid orgs in noid xfer dataframes
    noid_nonind_xfer_df = noid_nonind_xfer_df.merge(pcf_df[['PCFRegNumb','Committee']],how='left',left_on='DonorName',right_on='Committee')
    noid_nonind_xfer_df.columns = ['DonorName','DonorType','Committee','Category','target','value','source','DonorNameDrop']
    noid_nonind_xfer_df = noid_nonind_xfer_df.drop(['DonorNameDrop','DonorType'],axis=1)
    noid_ind_xfer_df = noid_ind_xfer_df.merge(pcf_df[['PCFRegNumb','Committee']],how='left',left_on='DonorName',right_on='Committee')
    noid_ind_xfer_df.columns = ['DonorName','Committee','Category','target','value','source','DonorNameDrop']
    noid_ind_xfer_df = noid_ind_xfer_df.drop('DonorNameDrop',axis=1)
    if ind_flag:
        noid_xfer_df = pd.concat([noid_nonind_xfer_df,noid_ind_xfer_df],ignore_index=True)
    else:
        noid_xfer_df = noid_nonind_xfer_df
    xfer_df = pd.concat([id_xfer_df[['source','target','value']],noid_xfer_df[['source','target','value']]])
    return xfer_df[xfer_df.source != xfer_df.target]

def write_xfer_data(filetype,output_dir,pcf_df,xfer_df,min_val):
    if filetype=='csv':
        write_xfer_csv(output_dir,pcf_df,xfer_df,min_val)
    elif filetype=='json':
        write_xfer_json(output_dir,pcf_df,xfer_df,min_val)
    else:
        raise('Invalid filetype value. Must be ''json'' or ''csv''')

def write_xfer_json(output_dir,pcf_df,xfer_df,min_val):
    d3_dict = {
        'nodes': [{'id': row.PCFRegNumb, 'name': row.Committee, 'kind': row.Kind} for _, row in pcf_df.iterrows()], # row.name gives you the index value. Lesson learned.
        'links': [{'source': int(row.source), 'target': int(row.target), 'value': row.value} for _, row in xfer_df.iterrows()],
    }
    with open(os.path.join(output_dir,f'./xfer_data_{min_val}.json'),'w') as wf:
        wf.write(json.dumps(d3_dict))

def write_xfer_csv(output_dir,pcf_df,xfer_df,min_val):
    pcf_df[['id','name']].to_csv(os.path.join(output_dir,f'./pcf_data_{min_val}.csv'))
    xfer_df[['source','target','value']].to_csv(os.path.join(output_dir,f'./xfer_data_{min_val}.csv'))

def main():
    args = parse_args()
    donor_table, pcf_table, xfer_table = get_cfb_data(args.data_dir)
    id_xfer_df = get_xfer_df(xfer_table,args.min_val)
    noid_nonind_xfer_df, noid_ind_xfer_df = get_noid_xfer_df(donor_table,args.min_val)
    id_pcf_df, noid_nonind_pcf_df, noid_ind_pcf_df = get_pcf_df(pcf_table,id_xfer_df,noid_nonind_xfer_df,noid_ind_xfer_df,args.ind)
    pcf_df = collect_pcf_df(id_pcf_df,noid_nonind_pcf_df,noid_ind_pcf_df,args.ind)
    xfer_df = collect_xfer_df(id_xfer_df,noid_nonind_xfer_df,noid_ind_xfer_df,pcf_df,args.ind)
    write_xfer_json(args.output_dir,pcf_df,xfer_df,args.min_val)

if __name__ == "__main__":
    main()