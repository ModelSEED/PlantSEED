#!/usr/bin/env python
import sys,json,re,os

Root_Class="Central_Carbon"
Subsystems=["AcetylCoA","Calvin","Glycolysis",
            "Pentose","RubiscoShunt","Photores","TCA"]

gene_publications=dict()
for ss in Subsystems:
    for dir_tuple in os.walk(Root_Class+"/"+ss):
        if('Done' in dir_tuple[0]):
            for gene_file in dir_tuple[2]:
                with open(dir_tuple[0]+'/'+gene_file) as gfh:
                    for line in gfh.readlines():
                        line=line.strip()
                        if(line == ""):
                            continue
                        array=line.split('\t')
                        if(array[0] not in gene_publications):
                            gene_publications[array[0]]=list()
                        gene_publications[array[0]].append(array[1])

with open('../../../Data/PlantSEED_v3/PlantSEED_Roles.json') as ps_roles_file:
    plantseed_roles = json.load(ps_roles_file)

for entry in plantseed_roles:
    for ftr in entry['features']:
        if(ftr in gene_publications):
            for pub in gene_publications[ftr]:
                entry['publications'].append(pub)

with open('../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as ps_roles_file:
    json.dump(plantseed_roles,ps_roles_file,indent=4)

