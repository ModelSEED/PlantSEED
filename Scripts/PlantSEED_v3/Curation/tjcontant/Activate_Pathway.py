#!/usr/bin/env python
import os,sys,json

if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
    print("Takes one argument, the path to and including pathway file")
    sys.exit()

pwy_file = sys.argv[1]

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

roles_dict=dict()
for entry in roles_list:
    roles_dict[entry['role']]=entry

with open(pwy_file) as pwy_file_handle:
    for line in pwy_file_handle.readlines():
        line=line.strip('\r\n')
        (rxn,role,ftr,pub,ss,cls,pwy,loc)=line.split('\t')

        if(role not in roles_dict):
            print("Warning: role ("+role+") not found in database")
            continue

        roles_dict[role]['include'] = True

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
