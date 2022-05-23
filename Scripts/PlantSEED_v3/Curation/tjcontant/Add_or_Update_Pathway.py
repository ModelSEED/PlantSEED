#!/usr/bin/env python
import os,sys,json,collections

if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
    print("Takes one argument, the path to and including pathway file")
    sys.exit()

pwy_file = sys.argv[1]

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

roles_dict = dict()
rxns_dict  = dict()
ftrs_dict  = dict()

# Adding roles to roles_dict and spontaneous_reactions
spontaneous_reactions = list()
for entry in roles_list:
    roles_dict[entry['role']]=entry
    if(entry['role'] == 'Spontaneous Reaction'):
        for reaction in entry['reactions']:
            if(reaction not in spontaneous_reactions):
                spontaneous_reactions.append(reaction)
    rxns_dict[entry['role']] = entry['reactions']
    ftrs_dict[entry['role']] = entry['features']

# Reading each line in biosynthesis file
with open(pwy_file) as pwy_file_handle:
    for line in pwy_file_handle.readlines():
        line=line.strip('\r\n')
        (rxn,role,ftr,pub,ss,cls,pwy,loc)=line.split('\t')

        # Check if role is new
        new_role = False
        if(role not in roles_dict):
            new_role = True
        elif(role == 'Spontaneous Reaction'):
            if(rxn not in spontaneous_reactions):
                new_role = True

        ####################################
        # UPDATE EXISTING ROLE
        if(new_role is False):
            print("Update Role\t" + role)

            # Convert rxn or ftr to list if string
            if(isinstance(rxns_dict[role], str)):
                rxns_dict[role] = rxns_dict[role].split()
            if(isinstance(ftrs_dict[role], str)):
                ftrs_dict[role] = ftrs_dict[role].split()

            # Split rxn and ftr if possible
            # Otherwise turn string into list
            if(';' in rxn): rxn = rxn.split(';')
            else: rxn = rxn.split()
            if(';' in ftr): ftr = ftr.split(';')
            else: ftr = ftr.split()

            # Find index of role
            for i in range(len(roles_list)):
                if(roles_list[i]['role'] == role): index = i

            ####################################
            # New reaction
            if(not set(rxn).issubset(set(rxns_dict[role]))):
                for entry in rxn:
                    if entry not in rxns_dict[role]:
                        roles_list[index]['reactions'].append(entry)
                        print("\t\t  new reaction:\t" + entry)

            ####################################
            # New feature
            elif(not set(ftr).issubset(set(ftrs_dict[role]))):
                for entry in ftr:
                    if entry not in ftrs_dict[role]:
                        roles_list[index]['features'].append(entry)
                        print("\t\t  new feature:\t" + entry)

            ####################################
            # New Localization
            loc_dict = dict()
            for entry in loc.split(';'):
                if(':' in entry):
                    (cpt,gene,sources)=entry.split(':')
                    loc_dict[gene]=sources.split('|')
                # Assumed reaction compartment
                else:
                    cpt=entry
                    loc_dict[gene]=[]

                if(cpt not in roles_list[index]['localization']):
                    roles_list[index]['localization'][cpt] = dict()
                roles_list[index]['localization'][cpt][gene]=loc_dict[gene]

        ####################################
        # ADD NEW ROLE
        else:
            print("New Role\t" + role)
            new_role = {'role':'',
                        'include':True,
                        'subsystems':[],
                        'classes':{},
                        'features':[],
                        'reactions':[],
                        'localization':{},
                        'publications':[]}

            ####################################
            # Add function
            new_role['role']=role

            ####################################
            # Add subsystem and class
            class_dict=dict()
            for entry in ss.split('||'):
                new_role['subsystems'].append(entry)
                class_dict[entry]=[]

                # Add pathway
                if(pwy != ""):
                    # One pathway for all classes
                    if (len(pwy.split('||')) == 1):
                        class_dict[entry].append(pwy)
                    # Pathway for each class
                    else:
                        # Check if each pathway defined for each class
                        if(pwy.split('||')[ss.split('||').index(entry)] != ""):
                            class_dict[entry].append(pwy.split('||')[ss.split('||').index(entry)])

            new_role['classes'][cls]=class_dict

            ####################################
            # Add reaction
            for entry in rxn.split(';'):
                new_role['reactions'].append(entry)

            ####################################
            # Add genes
            if(ftr != ""):
                for entry in ftr.split(';'):
                    new_role['features'].append(entry)

            ####################################
            # Add publications
            if(pub != ""):
                for entry in pub.split(','):
                    new_role['publications'].append(entry)

            ####################################
            # Add localization
            for entry in loc.split(';'):
                loc_dict=dict()
                #if protein localization data used
                if(':' in entry):
                    (cpt,gene,sources)=entry.split(':')
                    loc_dict[gene]=sources.split('|')
                #assumed reaction compartment
                else:
                    cpt=entry
                    loc_dict[rxn]=[]

                if(cpt not in new_role['localization']):
                    new_role['localization'][cpt] = dict()
                new_role['localization'][cpt][gene]=loc_dict[gene]

            ####################################
            # Update dictionaries and roles list
            roles_dict[role] = line
            rxns_dict[role] = rxn
            ftrs_dict[role] = ftr
            roles_list.append(new_role)

# Update roles file with new roles_list
with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)