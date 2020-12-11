#!/usr/bin/env python
import json

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

roles_dict=dict()
spontaneous_reactions=list()
for entry in roles_list:
    roles_dict[entry['role']]=entry
    if(entry['role'] == 'Spontaneous Reaction'):
        for reaction in entry['reactions']:
            if(reaction not in spontaneous_reactions):
                spontaneous_reactions.append(reaction)

with open('Add_Roles.txt') as roles_file:
    for line in roles_file.readlines():
        line=line.strip('\r\n')
        (cls,ss,pwy,role,rxn,ftr,pub,loc)=line.split('\t')

        new_role = False
        if(role not in roles_dict):
            new_role = True
        elif(role == 'Spontaneous Reaction'):
            if(rxn not in spontaneous_reactions):
                new_role = True

        if(new_role is True):
            new_role = {'role':'',
                        'include':True,
                        'subsystems':[],
                        'classes':{},
                        'features':[],
                        'reactions':[],
                        'localization':{},
                        'publications':[]}

            new_role['role']=role
            new_role['subsystems'].append(ss)

            class_dict={ss:[pwy]}
            new_role['classes'][cls]=class_dict

            new_role['reactions'].append(rxn)
            new_role['features'].append(ftr)
            new_role['publications'].append(pub)
            
            for entry in loc.split('||'):
                loc_dict=dict()
                (cpt,sources)=entry.split(':')
                loc_dict[ftr]=sources.split('|')
                new_role['localization'][cpt]=loc_dict
            
            roles_list.append(new_role)

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
#print(json.dumps(roles_list,indent=4))
