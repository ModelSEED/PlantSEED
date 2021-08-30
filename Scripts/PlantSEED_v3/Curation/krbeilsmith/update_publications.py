#!/usr/bin/env python
import os,sys,json

if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
    print("Takes one argument, the path to and including roles file")
    sys.exit()

updates_list=list()
with open(sys.argv[1]) as updates_file:
    for line in updates_file.readlines():
        line=line.strip('\r\n')
        
        array = line.split('\t')
        updates_dict=dict()
        for entry in array:
            (key,value) = entry.split(':', maxsplit=1)
            updates_dict[key]=value
        updates_list.append(updates_dict)

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

for update in updates_list:

    for entry in roles_list:

        if(update['feature'] in entry['features']):
            print("Updating: ",update['feature'])

            for publication in update['publications'].split('|'):
                if(publication not in entry['publications']):
                    entry['publications'].append(publication)
                    
with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
