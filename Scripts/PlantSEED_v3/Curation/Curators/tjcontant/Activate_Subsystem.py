#!/usr/bin/env python
import os,sys,json

subsystem = input('Enter subsystem: ')

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

roles_dict=dict()
for entry in roles_list:
    roles_dict[entry['role']]=entry

for entry in roles_list:
    if(subsystem in entry['subsystems'] and entry['include'] == False):
        entry['include'] = True
        print('  avtivated role: ' + entry['role'])

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
