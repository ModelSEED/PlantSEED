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
        (remove_cl_ss,add_cl_ss)=updates_dict[entry['role']].split('\t')

        #first remove
        (cls,ss) = remove_cl_ss.split(':')
        if(ss in entry['subsystems']):
            entry['subsystems'].remove(ss)

        if(cls in entry['classes'] and ss in entry['classes'][cls]):
            del(entry['classes'][cls][ss])
            if(len(entry['classes'][cls].keys())==0):
                del(entry['classes'][cls])

        #then add
        (cls,ss) = add_cl_ss.split(':')
        if(ss not in entry['subsystems']):
            entry['subsystems'].append(ss)

        if(cls not in entry['classes']):
            entry['classes'][cls]=dict()
        if(ss not in entry['classes'][cls]):
            entry['classes'][cls][ss]=[]

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
