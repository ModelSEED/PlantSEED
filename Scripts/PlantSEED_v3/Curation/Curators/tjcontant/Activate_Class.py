#!/usr/bin/env python
import os,sys,json

cls = input('Enter class:\t')
include_subcls = input('Subclass? (y/n)\t')
if(include_subcls != 'y'):
    subcls = ''
else:
    subcls = input('Enter subclass:\t')

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

roles_dict=dict()
for entry in roles_list:
    roles_dict[entry['role']]=entry

for entry in roles_list:
    if(cls in entry['classes'] and entry['include'] == False):
        if(subcls in entry['classes'][cls]):
            entry['include'] = True
            print('  avtivated role: ' + entry['role'])

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
