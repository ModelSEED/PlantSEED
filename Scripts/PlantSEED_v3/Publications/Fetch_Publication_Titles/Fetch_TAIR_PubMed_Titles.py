#!/usr/bin/env python
from urllib.request import urlopen
import sys,json,time,re

with open('../PlantSEED_Roles.json') as plantseed_file:
    plantseed=json.load(plantseed_file)

plantseed_ftrs=list()
for entry in plantseed:
    for ftr in entry['features']:
        if(ftr not in plantseed_ftrs):
            plantseed_ftrs.append(ftr)

prior_genes=list()
with open('Arabidopsis_TAIR_PubTitles.txt') as prior_file:
    for line in prior_file.readlines():
        line=line.strip()
        array=line.split('\t')
        prior_genes.append(array[0])

Input_File=open('TAIR_Locus_Published_20140331.txt')
URL='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?'
parameters=['db=pubmed','retmode=json','api_key=ac044fa222a809364c5b419b34cf2dac0d08']

Output_File=open('Arabidopsis_TAIR_PubTitles.txt','ab')
for line in Input_File.readlines():
    line=line.strip()
    array=line.split('\t')
    if(len(array)<3 or array[2] == ''):
        continue

    if(array[0] in prior_genes):
        continue

    gene = array[0]
    begin_match = re.search("^AT[\dCM]G",gene)
    if(begin_match == None):
        continue

    end_match = re.search("\.\d$",gene)
    if(end_match != None):
        gene=gene[:-2]

    if(gene not in plantseed_ftrs):
        continue

    response=urlopen(URL+'&'.join(parameters)+'&id='+array[2])
    MetaData=json.load(response)

    if(array[2] not in MetaData['result']):
        print("No response:",array[2],MetaData['result'])
        continue
    if('title' not in MetaData['result'][array[2]]):
        print("No document for ",array[2],MetaData['result'])
        continue

    Title=MetaData['result'][array[2]]['title']
    array.append(Title)
#    array[2]='=HYPERLINK("https://www.ncbi.nlm.nih.gov/pubmed/'+array[2]+'","'+array[2]+'")'
    line=('\t'.join(array))
    Output_File.write(line.encode('utf-8').strip()+"\n".encode('utf-8'))
Input_File.close()
Output_File.close()
