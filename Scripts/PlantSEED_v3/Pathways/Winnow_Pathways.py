#!/usr/bin/env python
#import sys,os.path,mimetypes,re,ssl,urllib,io
from urllib.request import urlopen
import json

MSD_url = 'https://raw.githubusercontent.com/ModelSEED/ModelSEEDDatabase/'
MSD_tag = 'v1.1.1'

Cyc_Rxns_Pwys=dict()
Pwys_Names=dict()
File = urlopen(MSD_url+MSD_tag+'/Biochemistry/Aliases/Provenance/MetaCyc_Pathways.tbl')
for line in File.readlines():
    line=line.decode()
    line=line.strip()
    array=line.split('\t')
    if(array[0] not in Cyc_Rxns_Pwys):
        Cyc_Rxns_Pwys[array[0]]=list()
    Cyc_Rxns_Pwys[array[0]].append(array[1])
    
    if(len(array)<3):
        Pwys_Names[array[1]]=array[1]
    else:
        Pwys_Names[array[1]]=array[2]

MS_Rxns_Pwys=dict()
File = urlopen(MSD_url+MSD_tag+'/Biochemistry/Aliases/Unique_ModelSEED_Reaction_Aliases.txt')
for line in File.readlines():
    line=line.decode()
    array=line.split('\t')
    if(array[1] in Cyc_Rxns_Pwys):
        if(array[0] not in MS_Rxns_Pwys):
            MS_Rxns_Pwys[array[0]]=list()
        for pwy in Cyc_Rxns_Pwys[array[1]]:
            MS_Rxns_Pwys[array[0]].append(pwy)

with open("../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

mpafh = open("Missing_Pathways.txt", "w")
mpafh.write("Class\tSubsystem\tRole\tPathway ID\tPathway Name\n")
for entry in roles_list:

    for role_class in entry['classes']:
        for role_ss in entry['classes'][role_class]:
            role_pwys = dict()
            for role_pwy in entry['classes'][role_class][role_ss]:
                role_pwys[role_pwy]=Pwys_Names[role_pwy]
            
            entry['classes'][role_class][role_ss]=role_pwys
            if(len(role_pwys.keys())==0):
                mpafh.write("\t".join([role_class,role_ss,entry['role']])+"\n")
mpafh.close()

with open('./PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)

