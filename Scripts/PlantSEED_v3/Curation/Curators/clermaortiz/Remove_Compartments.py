#!/usr/bin/env python
import json

roles_remove_cpt_dict=dict()
with open('Remove_Compartments.txt') as rmcpt_file:
    for line in rmcpt_file.readlines():
        line=line.strip('\r\n')
        (role,cpt)=line.split('\t')
        roles_remove_cpt_dict[role]=cpt

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

for entry in roles_list:
    if('Cytochrome b6-f' in entry['role']):
        if('d' not in entry['localization']):
            entry['localization']['d']=entry['localization']['c']
        del(entry['localization']['c'])

    if(entry['role'] in roles_remove_cpt_dict):
        del(entry['localization'][roles_remove_cpt_dict[entry['role']]])

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
