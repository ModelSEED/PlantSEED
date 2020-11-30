#!/usr/bin/env python
import sys,json,re

ftrs=dict()
pubs=dict()
titles=dict()
with open('Arabidopsis_PubSEED_PubTitles.txt') as pubseed_file:
    for line in pubseed_file.readlines():
        line=line.strip()
        array=line.split('\t')
        
        if(re.search('\.\d$',array[0])):
            array[0] = array[0][:-2]

        if(array[0] not in ftrs):
            ftrs[array[0]]=dict()

        if(array[2] not in ftrs[array[0]]):
            ftrs[array[0]][array[2]]=list()

        if('PubSEED' not in ftrs[array[0]][array[2]]):
            ftrs[array[0]][array[2]].append('PubSEED')

        if(array[2] not in pubs):
            pubs[array[2]]=list()

        if(array[0] not in pubs[array[2]]):
            pubs[array[2]].append(array[0])

        titles[array[2]]=array[4]+" ("+array[3]+")"

with open('Arabidopsis_TAIR_PubTitles.txt') as tair_file:
    for line in tair_file.readlines():
        line=line.strip()
        array=line.split('\t')

        if(re.search('\.\d$',array[0])):
            array[0] = array[0][:-2]

        if(array[0] not in ftrs):
            ftrs[array[0]]=dict()

        if(array[2] not in ftrs[array[0]]):
            ftrs[array[0]][array[2]]=list()

        if('TAIR' not in ftrs[array[0]][array[2]]):
            ftrs[array[0]][array[2]].append('TAIR')

        if(array[2] not in pubs):
            pubs[array[2]]=list()

        if(array[0] not in pubs[array[2]]):
            pubs[array[2]].append(array[0])

        titles[array[2]]=array[4]+" ("+array[3]+")"

with open('../PlantSEED_Roles.json') as ps_json:
    plantseed=json.load(ps_json)

ftr_roles=dict()
ftr_ss=dict()
for entry in plantseed:
    for ftr in entry['features']:
        if(ftr not in ftr_roles):
            ftr_roles[ftr]=list()
        ftr_roles[ftr].append(entry['role'])

        for ss in entry['subsystems']:
            if(ftr not in ftr_ss):
                ftr_ss[ftr]=list()
            if(ss not in ftr_ss[ftr]):
                ftr_ss[ftr].append(ss)

with open("Global_Subsystem_Publications.txt",'w') as ss_file:
    for ftr in sorted(ftrs.keys()):
        for pub in sorted(ftrs[ftr].keys()):
            if(len(pubs[pub])>5):
                continue
            ss_file.write("\t".join([ftr,pub,"/".join(ftr_roles[ftr]),"|".join(ftr_ss[ftr]),"|".join(sorted(ftrs[ftr][pub])),titles[pub]])+"\n")

