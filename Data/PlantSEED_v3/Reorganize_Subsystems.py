#!/usr/bin/env python
from urllib.request import urlopen
import sys,json,os

MSD_git_url = "https://raw.githubusercontent.com/ModelSEED/ModelSEEDDatabase/"
MSD_commit = "v1.1.1"

MS_Cyc_Aliases=dict()
Cyc_MS_Aliases=dict()
remote_file = urlopen(MSD_git_url+MSD_commit+"/Biochemistry/Aliases/Unique_ModelSEED_Reaction_Aliases.txt")
for line in remote_file.readlines():
    line=line.decode('utf-8')
    line=line.rstrip('\r\n')
    array=line.split('\t')

    if('Cyc' not in array[2]):
        continue

    if(array[1] not in Cyc_MS_Aliases):
        Cyc_MS_Aliases[array[1]]=list()
    if(array[0] not in MS_Cyc_Aliases):
        MS_Cyc_Aliases[array[0]]=list()
    if(array[0] not in Cyc_MS_Aliases[array[1]]):
        Cyc_MS_Aliases[array[1]].append(array[0])
    if(array[1] not in MS_Cyc_Aliases[array[0]]):
        MS_Cyc_Aliases[array[0]].append(array[1])

Cyc_Rxn_Pwy_Dict=dict()
Cyc_Pwy_Rxn_Dict=dict()
remote_file = urlopen(MSD_git_url+MSD_commit+"/Biochemistry/Aliases/Provenance/MetaCyc_Pathways.tbl")
for line in remote_file.readlines():
    line=line.decode('utf-8')
    line=line.rstrip('\r\n')
    array=line.split('\t')
    if(array[1] not in Cyc_Pwy_Rxn_Dict):
        Cyc_Pwy_Rxn_Dict[array[1]]=list()
    if(array[0] not in Cyc_Rxn_Pwy_Dict):
        Cyc_Rxn_Pwy_Dict[array[0]]=list()
    if(array[0] not in Cyc_Pwy_Rxn_Dict[array[1]]):
        Cyc_Pwy_Rxn_Dict[array[1]].append(array[0])
    if(array[1] not in Cyc_Rxn_Pwy_Dict[array[0]]):
        Cyc_Rxn_Pwy_Dict[array[0]].append(array[1])

classes_dict=dict()
with open("../PlantSEED_v1/All_Subsystems_PlantSEED_v1.txt") as all_subsystems:
    for line in all_subsystems.readlines():
        line=line.strip('\r\n')
        (cls,ss,pwy)=line.split('\t')
        if(cls not in classes_dict):
            classes_dict[cls]=dict()
        if(ss not in classes_dict[cls]):
            classes_dict[cls][ss]=list()
        if(pwy != ''):
            classes_dict[cls][ss].append(pwy)

#Publications
Root_Class="Central_Carbon"
Subsystems=["AcetylCoA","Calvin","Glycolysis",
            "Pentose","RubiscoShunt","Photores","TCA"]

gene_publications=dict()
for ss in Subsystems:
    for dir_tuple in os.walk("Publications/"+Root_Class+"/"+ss):
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

with open("../PlantSEED_v2.5/PlantSEED_Roles.json") as old_subsystem_file:
    old_roles_list = json.load(old_subsystem_file)

core_subsystem_list=list()
with open("Core_Subsystems_PlantSEED_v1.txt") as core_subsystems:
    for line in core_subsystems.readlines():
        line=line.strip()
        array=line.split('\t')
        core_subsystem_list.append(array[1])

new_roles_list=list()
for old_role in old_roles_list:
    new_role = {'role':'',
                'include':False,
                'subsystems':[],
                'classes':{},
                'features':[],
                'reactions':[],
                'localization':{},
                'publications':[]}

    new_role['role']=old_role['role']

    for ss in old_role['subsystems']:
        new_role['subsystems'].append(ss)
        if(ss in core_subsystem_list):
            new_role['include']=True
    
    localization_dict=dict()
    for ftr in old_role['features']:
        new_role['features'].append(ftr)

        if(ftr in gene_publications):
            for pub in gene_publications[ftr]:
                new_role['publications'].append(pub)

        for src in old_role['features'][ftr]:
            for cpt in old_role['features'][ftr][src]:
                if(cpt not in localization_dict):
                    localization_dict[cpt]=dict()
                if(ftr not in localization_dict[cpt]):
                    localization_dict[cpt][ftr]=list()
                localization_dict[cpt][ftr].append(src)

    for rxn in old_role['reactions']:
        new_role['reactions'].append(rxn)

        for cpt in old_role['reactions'][rxn]['cmpts']:
            if(cpt == ""):
                continue

            if(cpt not in localization_dict):
                localization_dict[cpt]=dict()
            if(rxn not in localization_dict[cpt]):
                localization_dict[cpt][rxn]=list()

    pathways=list()
    if('pathways' in old_role):
        for pwy in old_role['pathways']:
            if(pwy in Cyc_Pwy_Rxn_Dict):
                for cyc_rxn in Cyc_Pwy_Rxn_Dict[pwy]:
                    if(cyc_rxn in Cyc_MS_Aliases):
                        for ms_rxn in Cyc_MS_Aliases[cyc_rxn]:
                            if(ms_rxn in new_role['reactions'] and pwy not in pathways):
                                pathways.append(pwy)

    for cls in old_role['classes']:
        class_dict=dict()
        for ss in classes_dict[cls]:
            if(ss in old_role['subsystems']):
                if(ss not in class_dict):
                    class_dict[ss]=list()
                for pwy in classes_dict[cls][ss]:
                    if(pwy in pathways):
                        class_dict[ss].append(pwy)
        new_role['classes'][cls]=class_dict

    new_role['localization']=localization_dict

    new_roles_list.append(new_role)

with open('./PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(new_roles_list,new_subsystem_file,indent=4)
