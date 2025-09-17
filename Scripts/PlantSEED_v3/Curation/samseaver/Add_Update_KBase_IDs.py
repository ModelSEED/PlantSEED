#!/usr/bin/env python
import os,sys,json,hashlib,collections
with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
	roles_list = json.load(subsystem_file)

# list to store ID's
ID_list = list()
for entry in roles_list:

	# check if id does not exist
	if('kbase_id' not in entry.keys()):
		# string with unique info for each role
		# first reaction and subsystem included to differentiate spontaneous rxns
		str = entry['role'] + entry['reactions'][0] + entry['subsystems'][0]

		# create unique (truncated) hash ID from str and store in list
		entry_id = 'PS_role_' + hashlib.sha256(str.encode('utf-8')).hexdigest()[:6]

		# create new id if already in list
		while entry_id in ID_list:
			entry_id = 'PS_role_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]

		entry['kbase_id'] = entry_id
		print('New ID:\t' + entry_id + '\t' + entry['role'])

	# add id to list
	ID_list.append(entry['kbase_id'])

	# Need to Add Code for updating the identifiers of Complexes
	if(len(entry['compartmentalization'])==0):
		print("Missing Compartmentalization for ",entry['role'])
		continue

	for cpts in entry['compartmentalization']:
		if('kbase_ids' not in entry['compartmentalization'][cpts] or len(entry['compartmentalization'][cpts]['kbase_ids'])==0):
			for reaction in entry['reactions']:

				if(reaction == '14003'):
					print("Warning, reaction is EMPTY")

				# string with unique info for each complex
				str = entry['abstract_enzyme'] + " / " + entry['role'] + " / " + reaction + "_" + entry['compartmentalization'][cpts]['reaction']

				print(entry['role'],reaction,cpts,str)
				# create unique (truncated) hash ID from str and store in list
				entry_id = 'PS_complex_' + hashlib.sha256(str.encode('utf-8')).hexdigest()[:6]

				while(entry_id in ID_list):
					entry_id = 'PS_complex_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]

				if('kbase_ids' not in entry['compartmentalization'][cpts]):
					entry['compartmentalization'][cpts]['kbase_ids']=list()
					entry['compartmentalization'][cpts]['exclude']=False

				if(entry_id not in entry['compartmentalization'][cpts]['kbase_ids']):
					entry['compartmentalization'][cpts]['kbase_ids'].append(entry_id)

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
	json.dump(roles_list,new_subsystem_file,indent=4)
