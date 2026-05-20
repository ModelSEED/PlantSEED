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

updated_roles_dict=dict()
with open(sys.argv[1]) as updates_file:
	for line in updates_file.readlines():
		line=line.strip('\r\n')
		tmp_lst=line.split('\t')
		old_role = tmp_lst[1]
		updated_roles_dict[old_role]=tmp_lst

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
	roles_list = json.load(subsystem_file)

for entry in roles_list:
	if(entry['role'] in updated_roles_dict):
		lst = updated_roles_dict[entry['role']]
		entry['role'] = lst[2]
		
		for pub in lst[3].split('|'):
			entry['publications'].append(pub)
			
		if(lst[4] == 'include'):
			entry['include']=True
		if(lst[4] == 'exclude'):
			entry['include']=False
			
		if(lst[5] != ''):
			if('cofactors' not in entry):
				entry['cofactors']=list()
			entry['cofactors'].append(lst[5])
			
		if(lst[6] != '' and int(lst[6])>1):
			if('homomers' not in entry):
				entry['homomers']=lst[6]

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
	json.dump(roles_list,new_subsystem_file,indent=4)

with open("../../../../Data/PlantSEED_v3/Complex/Consolidated_PlantSEED_Complex_Curation.json") as complex_file:
	reactions_list = json.load(complex_file)
	
for rxn in reactions_list:
	for role in reactions_list[rxn]['roles']:
		if(role['role'] in updated_roles_dict):
			lst = updated_roles_dict[role['role']]
			role['role'] = lst[2]

with open("../../../../Data/PlantSEED_v3/Complex/Consolidated_PlantSEED_Complex_Curation.json",'w') as new_complex_file:
	json.dump(reactions_list,new_complex_file,indent=4)
		