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
        (role,ftr,locs)=line.split('\t')

        if(role not in roles_dict):
            print("Warning: role ("+role+") not found in database")
            continue

        if(ftr not in roles_dict[role]['features']):
            print("Warning: feature ("+ftr+") not found in database for "+role)
            continue

        loc_dict = roles_dict[role]['localization']
        for loc_data in locs.split('|'):
            (loc,source)=loc_data.split(':')

            if(loc not in loc_dict):
                loc_dict[loc]=dict()

            if(ftr not in loc_dict[loc]):
                loc_dict[loc][ftr] = list()

            if(source not in loc_dict[loc][ftr]):
                loc_dict[loc][ftr].append(source)

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
#print(json.dumps(roles_list,indent=4))
