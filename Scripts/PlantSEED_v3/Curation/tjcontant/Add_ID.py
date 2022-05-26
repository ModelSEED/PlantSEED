#!/usr/bin/env python
import os,sys,json,hashlib,collections
with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

# list to store ID's
ID_list = list()

for entry in roles_list:
    # string with unique info for each role
    # first reaction and subsystem included to differentiate spontaneous rxns
    str = entry['role'] + entry['reactions'][0] + entry['subsystems'][0]

    # create unique (truncated) hash ID from str and store in list
    entry['id'] = 'PS_role_' + hashlib.sha256(str.encode('utf-8')).hexdigest()[:6]
    ID_list.append(entry['id'])

# check for collisions (duplicate ID's)
duplicates = [item for item, count in collections.Counter(ID_list).items() if count > 1]
if(len(duplicates) > 0):
    print("Duplicate ID's: " + duplicates)
else:
    print("No duplicates!")


with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
