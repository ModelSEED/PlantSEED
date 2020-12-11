#!/usr/bin/env python
import json

with open("../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

roles_dict=dict()
for entry in roles_list:
    roles_dict[entry['role']]=entry

new_roles_list=list()
for role in sorted(roles_dict.keys()):
    new_roles_list.append(roles_dict[role])

with open('../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(new_roles_list,new_subsystem_file,indent=4)
