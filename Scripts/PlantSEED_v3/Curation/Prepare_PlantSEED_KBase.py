#!/usr/bin/env python
import os,sys,json,copy
import hashlib
# Open database
script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
database_relative_path = os.path.join(script_directory, "../../../", "Data/PlantSEED_v3/")
with open(os.path.join(database_relative_path, "PlantSEED_Roles.json")) as subsystem_file:
	roles_list = json.load(subsystem_file)

role_ID_list = list()
complex_ID_dict = dict()

reactions_roles = dict()
roles_reactions = dict()
roles_enzymes = dict()
enzymes_roles = dict()
# string with unique info for each role
# first reaction and subsystem included to differentiate spontaneous rxns
# str = entry['role'] + entry['reactions'][0] + entry['subsystems'][0]

# string with unique info for each complex
# str = entry['abstract_enzyme'] + " / " + entry['role'] + " / " + reaction + "_" + entry['compartmentalization'][cpts]['reaction']

# Collect all enzymes/reactions/roles and kbase identifiers first
for entry in roles_list:

	if('abstract_enzyme' not in entry or 'role' not in entry or 'reactions' not in entry or 'localization' not in entry):
		print("Warning, missing abstract_enzyme, role, reactions, or compartments for role: "+entry['role'])
		print("\tCannot create unique KBase Complex ID")
			
	if('abstract_enzyme' not in entry):
		print("Warning, missing abstract_enzyme for role: "+entry['role'])
	elif(entry['abstract_enzyme'] == entry['role']):
		if('transport' not in entry['abstract_enzyme'] and 'Spontaneous' not in entry['role']):
			print("Warning, abstract_enzyme is the same as role: "+entry['role'])
	else:
		roles_enzymes[entry['role']] = entry['abstract_enzyme']
		if(entry['abstract_enzyme'] not in enzymes_roles):
			enzymes_roles[entry['abstract_enzyme']]=list()
		if(entry['role'] not in enzymes_roles[entry['abstract_enzyme']]):
			enzymes_roles[entry['abstract_enzyme']].append(entry['role'])
	
	if('kbase_id' in entry):
		if('kbase_id' in role_ID_list):
			print("Warning, duplicate kbase_id: "+entry['kbase_id'] + " for role: "+entry['role'])
		else:
			role_ID_list.append(entry['kbase_id'])


	if('compartmentalization' in entry):

		for cpt in entry['compartmentalization']:

			cpx_dict = entry['compartmentalization'][cpt]
		
			if('kbase_ids' in cpx_dict):
					for kbase_id in cpx_dict['kbase_ids']:
						if(kbase_id not in complex_ID_dict):
							complex_ID_dict[kbase_id]=list()
						for rxn_cpt in cpx_dict['kbase_ids'][kbase_id]:
							if(rxn_cpt not in complex_ID_dict[kbase_id]):
								complex_ID_dict[kbase_id].append(rxn_cpt)

	if('reactions' in entry):
		for rxn in entry['reactions']:
			if(entry['role'] not in roles_reactions):
				roles_reactions[entry['role']]=list()
			if(rxn not in roles_reactions[entry['role']]):
				roles_reactions[entry['role']].append(rxn)

			if(rxn not in reactions_roles):
				reactions_roles[rxn]=list()
			if(entry['role'] not in reactions_roles[rxn]):
				reactions_roles[rxn].append(entry['role'])

# Go back through database
updated_roles = False
for entry in roles_list:

	if('kbase_id' not in entry):

		# check if all fields available to form unique role id
		if('role' not in entry or 'reactions' not in entry or 'subsystems' not in entry \
	 		or len(entry['reactions'])==0 or len(entry['subsystems'])==0):
			print("Warning, missing role, reactions, or subsystems for role: "+entry['role'])
			print("\tCannot create unique KBase Role ID")
			continue
		else:
			# string with unique info for each role
			# first reaction and subsystem included to differentiate spontaneous rxns
			# print(entry['role'],entry['reactions'],entry['subsystems'])
			role_str = entry['role'] + entry['reactions'][0] + entry['subsystems'][0]

			# create unique (truncated) hash ID from str and store in list
			entry_id = 'PS_role_' + hashlib.sha256(role_str.encode('utf-8')).hexdigest()[:6]

			# create new id if already in list
			while entry_id in ID_list:
				entry_id = 'PS_role_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]

			entry['kbase_id'] = entry_id
			print('New ID:\t' + entry_id + '\t' + entry['role'])
			updated_roles=True
			pass

	if('compartmentalization' not in entry):
		entry['compartmentalization'] = dict()

		for cpt in entry['localization']:
			cpx_dict = {'reaction':cpt,'kbase_ids':{},'exclude':False}
			for rxn in entry['reactions']:
				tmpl_rxn = rxn+"_"+cpt

				if(tmpl_rxn not in reactions_roles):
					print("Warning: template_reaction not found: "+tmpl_rxn)
					continue

				enzymes = list()
				for role in reactions_roles[tmpl_rxn]:
					if(role not in roles_enzymes):
						print("Warning: role not found :"+role)

					if(roles_enzymes[role] not in enzymes):
						enzymes.append(roles_enzymes[role])

				tmpl_rxns = list()
				for enzyme in enzymes:
					for role in enzymes[enzyme]:
						for rxn in roles_reactions[role]:
							if(rxn not in tmpl_rxns):
								tmpl_rxns.append(rxn)

				sorted_enzymes = sorted(enzymes)
				sorted_roles = sorted(reactions_roles[tmpl_rxn])
				sorted_reactions = sorted(tmpl_rxns)

				# string with unique info for each complex
				cpx_str = " / ".join(sorted_enzymes) + " / " + " / ".join(sorted_roles) + " / " + " / ".join(sorted_reactions)

				# generate unique hash of complex string
				entry_id = 'PS_complex_' + hashlib.sha256(cpx_str.encode('utf-8')).hexdigest()[:6]
				while(entry_id in complex_ID_dict):
					entry_id = 'PS_complex_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]
				
				if(entry_id not in cpx_dict['kbase_ids']):
					cpx_dict['kbase_ids'][entry_id]=list()
					updated_roles=True
				if(tmpl_rxn not in cpx_dict['kbase_ids'][entry_id]):
					cpx_dict['kbase_ids'][entry_id].append(tmpl_rxn)

if(updated_roles is True):
	with open(os.path.join(database_relative_path, "PlantSEED_Roles.json"),'w') as new_subsystem_file:
		json.dump(roles_list,new_subsystem_file,indent=4)