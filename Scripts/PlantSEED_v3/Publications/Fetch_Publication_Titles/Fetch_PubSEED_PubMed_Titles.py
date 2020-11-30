#!/usr/bin/env python
from urllib.request import urlopen
import sys,json,time

with open('../PlantSEED_Roles.json') as plantseed_file:
    plantseed=json.load(plantseed_file)

plantseed_ftrs=list()
for entry in plantseed:
    for ftr in entry['features']:
        if(ftr not in plantseed_ftrs):
            plantseed_ftrs.append(ftr)

# Arabidopsis PubSEED publications retrieved from
# /vol/public-pseed/FIGdisk/FIG/Data/Organisms/3702.11/Features/peg/tbl
File=open('Arabidopsis_PubSEED_Pubs.txt')
URL='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?'
parameters=['db=pubmed','retmode=json','api_key=ac044fa222a809364c5b419b34cf2dac0d08']

Lines=list()
for line in File.readlines():
    line=line.strip()
    array=line.split('\t')
    if(len(array)<3):
        continue

    if(array[0] not in plantseed_ftrs):
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
    Lines.append('\t'.join(array))
File.close()

File=open('Arabidopsis_PubSEED_PubTitles.txt','wb')
for line in Lines:
    File.write(line.encode('utf-8').strip()+"\n".encode('utf-8'))
File.close()
