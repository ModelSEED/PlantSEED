#!/usr/bin/env python
import os,sys,json,csv,math
import pandas as pd
from pprint import pprint

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json') as subsystem_file:
    roles_list = json.load(subsystem_file)


# user input
SUBSYSTEM = 'Homomethionine_biosynthesis_and_methionine_chain_elongation_pathway_for_glucosinolates_in_plants'
FILE_NAME = 'glucosinolate_psi.json'
THRESHOLD = 0.85
BRASSICACEAE = ['Alyrata_v1.0', 'Alyrata_v2.1', 'Athaliana_Araport11', 'Athaliana_TAIR10', 'Boleraceacapitata_v1.0', 'Bstricta_v1.2', 'Cgrandiflora_v1.1', 'Crubella_v1.0', 'Crubella_v1.1', 'Esalsugineum_v1.0', 'Sparvula_v2.2']

# find genes in SUBSYSTEM
gene_list = list()
for entry in roles_list:
    if(SUBSYSTEM in entry['subsystems']):
        for gene in entry['features']:
            gene_list.append(gene.split('||')[1])

# read in orthogroup data and create dataframe/dictoinary
df = pd.read_csv('Orthogroups.tsv', sep='\t', low_memory=False)
protein_fam_df = pd.DataFrame()
protein_fam_dict = dict()

# add ortholog information to protein_fam_dict
for gene in gene_list:
    # locating row(s) in the TAIR10 column that contain the gene
    matches = df.loc[df['Athaliana_TAIR10'].str.contains(gene, na = False)]
    if(len(matches) == 0):
        protein_fam_dict[gene] = None
        print('Gene not found in Orthogroups.tsv: ' + gene)
    else:
        protein_fam_dict[gene] = matches.to_dict(orient = 'dict')


# function to get 'deepest' values from nested dictionary
def iter_leafs(d):
    for key, val in d.items():
        if isinstance(val, dict):
            yield from iter_leafs(val)
        else:
            val = str(val)
            if(val != 'nan'):
                yield val.split(', ')

# function to remove null values from nested dictionary
def cleanNullTerms(d):
   clean = {}
   for k, v in d.items():
      if isinstance(v, dict):
         nested = cleanNullTerms(v)
         if len(nested.keys()) > 0:
            clean[k] = nested
      elif v is not None:
         clean[k] = v
   return clean

# function to remove speces that have no genes in protein family
def removeEmptySpecies(d):
    include = {}
    for k0, v0 in d.items():
        include[k0] = {}
        include[k0]['genomes'] = {}
        for k1, v1 in v0['genomes'].items():
            if (d[k0]['genomes'][k1]['total_genes'] != 0):
                include[k0]['genomes'][k1] = d[k0]['genomes'][k1]
    return include


# create new diciotnary with new structure
new_dict = dict()
for key in protein_fam_dict:
    ortho_key = key # + ' (' + list(iter_leafs(protein_fam_dict[key]))[0][0] + ')'
    new_dict[ortho_key] = {'genomes': {}}
    genes = list(iter_leafs(protein_fam_dict[key]))[1:]

    for species in genes:
        genome_key = species[0].split('||')[0]
        new_dict[ortho_key]['genomes'][genome_key] = {'family': 'Not Brassicaceae', 'total_genes': int(), 'genes': {}}


        for i in range(0, len(species)):
            species[i] = species[i].split('||')[1]
            new_dict[ortho_key]['genomes'][genome_key]['genes'][species[i]] = None

        if(genome_key in BRASSICACEAE):
            new_dict[ortho_key]['genomes'][genome_key]['family'] = 'Brassicaceae'

# add sequence alignment data to new_dict
for key in new_dict:
    accession_num = list(iter_leafs(protein_fam_dict[key]))[0][0]
    psi_file = 'PSI/' + accession_num + '.txt'
    psi_df = pd.read_csv(psi_file, sep = '\t', header = None)

    gene_string = 'Athaliana_TAIR10||' + key
    # make sure collumn has correct gene
    matches_pre = psi_df.loc[psi_df[1].str.contains(key)]
    # make sure collumn is from correct genome annotation
    matches = matches_pre.loc[matches_pre[1].str.contains('Athaliana_TAIR10')]

    for row in range(0, len(matches)):
        match = matches.iloc[row][2]
        abbr_match = match.split('||')[1].split(':')[0]
        for k0, v0 in new_dict.items():
            for k1, v1 in v0['genomes'].items():
                for k2, v2 in v1['genes'].items():
                    if(k2 == abbr_match and matches.iloc[row][3] >= THRESHOLD):
                        new_dict[k0]['genomes'][k1]['genes'][k2] = matches.iloc[row][3]


# remove null terms from new_dict
new_dict = cleanNullTerms(new_dict)

# add up total_genes for each genome
for k0, v0 in new_dict.items():
    for k1, v1 in v0['genomes'].items():
        if('genes' in v1.keys()):
            new_dict[k0]['genomes'][k1]['total_genes'] = len(new_dict[k0]['genomes'][k1]['genes'])

# remove genomes that have no genes in protein family
new_dict = removeEmptySpecies(new_dict)

# add up brassicaceae and non-brassicaceae genes in each protein family
for k0, v0 in new_dict.items():
    sum_brassicaceae = 0
    sum_not_brassicaceae = 0
    for k1, v1 in v0['genomes'].items():
        if new_dict[k0]['genomes'][k1]['family'] == 'Brassicaceae':
            sum_brassicaceae += new_dict[k0]['genomes'][k1]['total_genes']
        else:
            sum_not_brassicaceae += new_dict[k0]['genomes'][k1]['total_genes']
    new_dict[k0]['total_brassicaceae_genes'] = sum_brassicaceae
    new_dict[k0]['total_not_brassicaceae_genes'] = sum_not_brassicaceae


# save dictionary as JSON file
JSON_file = open(FILE_NAME, "w")
json.dump(new_dict, JSON_file, indent = 4)
JSON_file.close()

# print dictionary to console
print(json.dumps(new_dict, indent = 4))
