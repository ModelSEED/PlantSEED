#!/usr/bin/env python
import os,sys,json,csv,math
from pprint import pprint
import pandas as pd

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json') as subsystem_file:
    roles_list = json.load(subsystem_file)

# user input
SUBSYSTEM = input('\nEnter subsystem:\t')
FILE_NAME = input('Create csv filename:\t')

# list to store genes within specified subsystem
gene_list = list()

# if role contains SUBSYSTEM, then append the genes
for entry in roles_list:
    if(SUBSYSTEM in entry['subsystems']):
        for gene in entry['features']:
            gene_list.append(gene.split('||')[1])

with open('Orthogroups.tsv') as orthogroups_file:

    #read in orthogroup data
    df = pd.read_csv('Orthogroups.tsv', sep='\t', low_memory=False)

    # create dataframe and dict to store data
    protein_fam_df = pd.DataFrame()
    protein_fam_dict = dict()

    # find proteins families for genes in gene_list
    for gene in gene_list:
        # locating row(s) in the TAIR10 column that contain the gene
        matches = df.loc[df['Athaliana_TAIR10'].str.contains(gene, na = False)]
        if(len(matches) == 0):
            protein_fam_dict[gene] = None
            print('\n Gene not found in Orthogroups.tsv: ' + gene)
        else:
            protein_fam_df = pd.concat([protein_fam_df, matches])
            protein_fam_dict[gene] = matches.to_dict(orient = 'dict')

    # print list of genes in subsystem (from gene_list)
    print('\n\nTAIR10 genes in subsystem: \n')
    pprint(gene_list)

    # print summary of dataframe
    print('\n\nProtein family dataframe:\n')
    print(protein_fam_df)

    # function to get 'deepest' values from nested dictionary
    def iter_leafs(d):
        for key, val in d.items():
            if isinstance(val, dict):
                yield from iter_leafs(val)
            else:
                val = str(val)
                if(val != 'nan'):
                    yield val.split(', ')

    # create new diciotnary using iter_leafs function
    new_dict = dict()
    for key in protein_fam_dict:
        new_dict[key] = list(iter_leafs(protein_fam_dict[key]))

        # combining species lists into one list
        final_list = list()
        for item in new_dict[key]:
            final_list += item
        new_dict[key] = final_list

        # renaming key to include orthogroup number
        # then delete orthogroup number from list
        new_key = key + ' (' + final_list[0] + ')'
        final_list.pop(0)
        new_dict[new_key] = new_dict.pop(key)

    # print new dictionary if user desires
    print_dict = input('\n\nPrint protein family dict? (y/n)  ')
    print('\n')
    if(print_dict == 'y'): pprint(new_dict)
