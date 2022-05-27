#!/usr/bin/env python
import os,sys,json,hashlib,collections
with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

# list to store ID's
ID_list = list()

for entry in roles_list:

    # check if id does not exist
    if('kbase_id' not in entry.keys()):
        # string with unique info for each role
        # first reaction and subsystem included to differentiate spontaneous rxns
        str = entry['role'] + entry['reactions'][0] + entry['subsystems'][0]

        # create unique (truncated) hash ID from str and store in list
        entry_id = 'PS_role_' + hashlib.sha256(str.encode('utf-8')).hexdigest()[:6]

        # create new id if already in list
        while entry_id in ID_list:
            entry_id = 'PS_role_' + hashlib.sha256(str.encode('utf-8')).hexdigest()[:6]

        entry['kbase_id'] = entry_id
        print('New ID:\t' + entry_id + '\t' + entry['role'])

    # add id to list
    ID_list.append(entry['kbase_id'])

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
