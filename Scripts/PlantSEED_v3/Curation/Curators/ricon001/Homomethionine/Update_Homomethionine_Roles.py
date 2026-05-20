#!/usr/bin/env python
import os,sys,json

if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
	print("Takes one argument, the path to and including roles file")
	sys.exit()

# headers are:
# 0 gene
# 1 old role (if present)
# 2 new role
# 3 publications
# 4 activate/include
# 5 cofactor formula
# 6 homomerism

# can include "ADD/REMOVE"

updated_roles_dict=dict()
add_dict=dict()
rem_dict=dict()
with open(sys.argv[1]) as updates_file:
	for line in updates_file.readlines():
		line=line.strip('\r\n')
		tmp_lst=line.split('\t')
		print(tmp_lst)
		if(tmp_lst[1] == "ADD"):
			if(tmp_lst[0] not in add_dict):
				add_dict[tmp_lst[0]]=dict()
			if(tmp_lst[2] not in add_dict[tmp_lst[0]]):
				add_dict[tmp_lst[0]][tmp_lst[2]]=dict()
			add_dict[tmp_lst[0]][tmp_lst[2]][tmp_lst[3]]=1
			if(len(tmp_lst)>4):
				add_dict[tmp_lst[0]][tmp_lst[2]][tmp_lst[3]]=tmp_lst[4]
			
		elif(tmp_lst[1] == "REMOVE"):
			if(tmp_lst[0] not in rem_dict):
				rem_dict[tmp_lst[0]]=dict()
			if(tmp_lst[2] not in rem_dict[tmp_lst[0]]):
				rem_dict[tmp_lst[0]][tmp_lst[2]]=list()
			rem_dict[tmp_lst[0]][tmp_lst[2]].append(tmp_lst[3])	

		else:
			old_role = tmp_lst[1]
			updated_roles_dict[old_role]=tmp_lst

with open("../../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
	roles_list = json.load(subsystem_file)

for entry in roles_list:
	updated_role=False
	if(entry['role'] in updated_roles_dict):
		lst = updated_roles_dict[entry['role']]
		entry['role'] = lst[2]
		
		for pub in lst[3].split('|'):
			if(pub != ""):
				entry['publications'].append(pub)
			
		if(lst[4] == 'include'):
			entry['include']=True
		if(lst[4] == 'exclude'):
			entry['include']=False
			
		if(len(lst)>5 and lst[5] != ''):
			if('cofactors' not in entry):
				entry['cofactors']=list()
			entry['cofactors'].append(lst[5])
			
		if(len(lst)>6 and lst[6] != '' and int(lst[6])>1):
			if('homomers' not in entry):
				entry['homomers']=lst[6]

		updated_role=True

	if(entry['role'] in add_dict):
		for field in add_dict[entry['role']]:
			for input in add_dict[entry['role']][field].keys():
				print("ADD",field,input)
				entry[field].append(input)

				# Update localization
				if(field == 'features'):
					for cpt in entry['localization']:
						
						if(add_dict[entry['role']][field][input] in entry['localization'][cpt]):
							entry['localization'][cpt][input] = entry['localization'][cpt][add_dict[entry['role']][field][input]]

		updated_role=True

	if(entry['role'] in rem_dict):
		for field in rem_dict[entry['role']]:
			for input in rem_dict[entry['role']][field]:
				entry[field].remove(input)

				if(field == 'features'):
					for cpt in entry['localization']:
						if(input in entry['localization'][cpt]):
							del(entry['localization'][cpt][input])

		updated_role=True

	if(updated_role is True):
		entry['curators'].append('riocon001')
		if('samseaver' not in entry['curators']):
			entry['curators'].append('samseaver')

with open('../../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
	json.dump(roles_list,new_subsystem_file,indent=4)

"""
with open("../../../../../Data/PlantSEED_v3/Complex/Consolidated_PlantSEED_Complex_Curation.json") as complex_file:
	reactions_list = json.load(complex_file)

for rxn in reactions_list:
	for role in reactions_list[rxn]['roles']:
		if(role['role'] in updated_roles_dict):
			lst = updated_roles_dict[role['role']]
			role['role'] = lst[2]

with open("../../../../../Data/PlantSEED_v3/Complex/Consolidated_PlantSEED_Complex_Curation.json",'w') as new_complex_file:
	json.dump(reactions_list,new_complex_file,indent=4)
"""