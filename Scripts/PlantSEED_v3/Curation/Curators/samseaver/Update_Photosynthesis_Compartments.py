#!/usr/bin/env python
import os,sys,json

if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
	print("Takes one argument, the path to and including reactions file")
	sys.exit()

# headers are:
# 0 role
# 1 reaction
# 2 old comparment
# 3 feature
# 4 new compartment

updated_roles_dict=dict()
with open(sys.argv[1]) as updates_file:
	for line in updates_file.readlines():
		line=line.strip('\r\n')
		tmp_lst=line.split('\t')
		old_role = tmp_lst[0]
		if(old_role not in updated_roles_dict):
			updated_roles_dict[old_role]=list()
		updated_roles_dict[old_role].append(tmp_lst)
	
with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
	roles_list = json.load(subsystem_file)

#replace compartments with features
#PSII, Cyto-b6f, ATPSyn
ps_rxn_list=('rxn20632','rxn20595','rxn08173')
for entry in roles_list:
	if(entry['role'] not in updated_roles_dict):
		continue
	
	for line in updated_roles_dict[entry['role']]:
		if(line[2] in entry['localization']):
			old_dct = entry['localization'][line[2]]
			del(entry['localization'][line[2]])
			
			entry['localization'][line[4]]=old_dct

		if(line[3] not in entry['localization'][line[4]]):
			print(line[3])

#replace empty compartments
ps_ss_list = ['Photosystem_II',
			'Cytochrome_b6-f_complex_in_plants_(plastidial)_and_cyanobacteria',
			'F0F1-type_ATP_synthase_in_plants_(plastidial)']
for entry in roles_list:
	in_ss=False
	for ss in entry['subsystems']:
		if(ss in ps_ss_list):
			in_ss=True

	if(in_ss is False):
		continue

	if('d' in entry['localization']):
		entry['localization']['dy']=entry['localization']['d']
		del(entry['localization']['d'])

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
	json.dump(roles_list,new_subsystem_file,indent=4)
