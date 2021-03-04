#!/usr/bin/env python
import sys,json

if(len(sys.argv)!=2):
    print("Takes one argument, the name of the subsystem, for example: 'Choline_biosynthesis_in_plants'")
    sys.exit()

included_subsystem = sys.argv[1]

with open("../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

for entry in roles_list:
    if(included_subsystem in entry['subsystems']):
        entry['include']=True

with open('../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
