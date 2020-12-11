#!/usr/bin/env python
import json

with open("../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

new_roles_list=list()
for role in sorted(roles_list, key = lambda entry:entry['role']):
    new_roles_list.append(role)

with open('../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(new_roles_list,new_subsystem_file,indent=4)
