#!/usr/bin/env python
import os,sys,json

if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
    print("Takes one argument, the path to and including roles file")
    sys.exit()

updates_dict=dict()
with open(sys.argv[1]) as updates_file:
    for line in updates_file.readlines():
        line=line.strip('\r\n')
        (role,line)=line.split('\t',maxsplit=1)
        updates_dict[role]=line

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

for entry in roles_list:
    if(entry['role'] in updates_dict):
        for update in updates_dict[entry['role']].split('\t'):
            (key,values)=update.split(':')
            for value in values.split(','):
                if(value not in entry[key]):
                    entry[key].append(value)
        
            # Placeholder for updating localization data if available
            if(key == 'features' or key == 'reactions'):
                pass

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
