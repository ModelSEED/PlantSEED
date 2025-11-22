#!/usr/bin/env python
import os,sys,json,copy
import hashlib
# Open database
script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
database_relative_path = os.path.join(script_directory, "../../../", "Data/PlantSEED_v3/")
with open(os.path.join(database_relative_path, "PlantSEED_Roles.json")) as subsystem_file:
	roles_list = json.load(subsystem_file)

print("+"*30)
print("++ Checking KBase Role IDs")
role_ID_list = list()

# Collect all role identifiers first
for entry in roles_list:
	
	if('kbase_id' in entry):
		if(entry['kbase_id'] in role_ID_list):
			print("Warning, duplicate kbase_id: "+entry['kbase_id'] + " for role: "+entry['role'])
		else:
			role_ID_list.append(entry['kbase_id'])

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
			role_str = entry['role'] + entry['reactions'][0] + entry['subsystems'][0]

			# create unique (truncated) hash ID from str and store in list
			entry_id = 'PS_role_' + hashlib.sha256(role_str.encode('utf-8')).hexdigest()[:6]

			# create new id if already in list
			while entry_id in role_ID_list:
				entry_id = 'PS_role_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]

			role_ID_list.append(entry_id)

			entry['kbase_id'] = entry_id
			updated_roles=True
			pass

print("+"*30)


print("+"*30)
print("++ Checking KBase Complex IDs")

with open(os.path.join(database_relative_path, "PlantSEED_Complexes.json")) as subsystem_file:
	complexes_list = json.load(subsystem_file)

# Collect all complex identifiers first
update_complexes=False
complex_ID_list = list()
current_enzyme_dict = dict()
for entry in complexes_list:

	update_complex=False	
	if('kbase_id' in entry):
		if(entry['kbase_id'] in complex_ID_list):
			print("Warning, duplicate kbase_id: "+entry['kbase_id'] + " for enzyme: "+entry['enzyme'])
		else:
			complex_ID_list.append(entry['kbase_id'])

		enz = entry['enzyme']
		if(enz not in current_enzyme_dict):
			current_enzyme_dict[enz]={'rles':[],'rxns':[]}

		roles = sorted(entry['roles'])
		for role in roles:
			if(role not in current_enzyme_dict[enz]):
				current_enzyme_dict[enz]['rles'].append(role)

		rxns_cpts = list()
		for cpt_id in entry['compartments_reactions']:
			cpt = entry['compartments_reactions'][cpt_id]
			for rxn in cpt['reactions']:
				rxn_cpt = rxn+'_'+cpt_id
				if(rxn_cpt not in current_enzyme_dict[enz]['rxns']):
					current_enzyme_dict[enz]['rxns'].append(rxn_cpt)
				if(rxn_cpt not in rxns_cpts):
					rxns_cpts.append(rxn_cpt)

		rxns_cpts = sorted(rxns_cpts)
		cpx_str = " / ".join([enz,"|".join(roles),"|".join(rxns_cpts)])
		kbase_id = 'PS_complex_' + hashlib.sha256(cpx_str.encode('utf-8')).hexdigest()[:6]
		if(kbase_id != entry['kbase_id']):
			print("Updating kbase_id for: ",cpx_str)
			entry['kbase_id']=kbase_id
			update_complex = True
	
	if(update_complex is True):
		update_complexes = True

# Go back through roles database and for any enzyme/role/reaction combination that doesn't have a complex id
# and create a new complex for them
new_enzyme_dict = dict()
for entry in roles_list:
	if('abstract_enzyme' not in entry):
		print("Warning: entry with role: "+entry['role']+" doesn't have an enzyme name")
		continue

	enz = entry['abstract_enzyme']

	# special case of Spontaneous Reaction
	if(enz.lower() == 'spontaneous reaction'):
		# the entry always has a single spontaneous reaction
		# but as there's no enzyme, we need to distinguish 
		# between each one here
		enz = enz+"||"+entry['reactions'][0]

	if enz in current_enzyme_dict:
		if(entry['role'] not in current_enzyme_dict[enz]['rles']):
			print("Warning: role name has changed for ",enz)
		for rxn in entry['reactions']:
			for lcz in entry['localization']:
				rxn_cpt = rxn+'_'+lcz
				if(len(lcz) == 1 and rxn_cpt not in current_enzyme_dict[enz]['rxns']):
					print("Warning: reaction has changed for ",enz,current_enzyme_dict[enz]['rxns'],rxn_cpt)
				if(len(lcz)==2):
					fd_rxn=False
					for subcpt in lcz:
						if(rxn+"_"+subcpt in current_enzyme_dict[enz]['rxns']):
							fd_rxn=True
					if(fd_rxn is False):
						print("Warning: reaction has changed for ",enz,current_enzyme_dict[enz]['rxns'],rxn_cpt)
	else:
		print("New enzyme!")
		# here, I'm assuming that the first time you encounter a new enzyme name
		# is the first time you encounter the roles and reactions that should be
		# associated with the enzyme, so any successive entries should be added here
		if(enz not in new_enzyme_dict):
			new_enzyme_dict[enz]={'rles':[],'rxns':[],'cpts':[]}
		if(entry['role'] not in new_enzyme_dict[enz]['rles']):
			new_enzyme_dict[enz]['rles'].append(entry['role'])
		for rxn in entry['reactions']:
			for lcz in entry['localization']:
				rxn_cpt = rxn+"_"+lcz
				if(rxn_cpt not in new_enzyme_dict[enz]['rxns']):
					new_enzyme_dict[enz]['rxns'].append(rxn_cpt)
				if(lcz not in new_enzyme_dict[enz]['cpts']):
					new_enzyme_dict[enz]['cpts'][lcz]={'reactions':[],"reagents":lcz,"exclude":False}
				if(rxn not in new_enzyme_dict[enz]['cpts'][lcz]['reactions']):
					new_enzyme_dict[enz]['cpts'][lcz]['reactions'].append(rxn)

# re-build complexes to insert into PlantSEED_Complexes and generate a new id
for enz in new_enzyme_dict:
	rxns = sorted(new_enzyme_dict[enz]['rxns'])
	rles = sorted(new_enzyme_dict[enz]['rles'])
	cpx_str = " / ".join([enz,"|".join(rles),"|".join(rxns)])
	kbase_id = 'PS_complex_' + hashlib.sha256(cpx_str.encode('utf-8')).hexdigest()[:6]
	while entry_id in complex_ID_list:
		entry_id = 'PS_role_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]

	complex = {'kbase_id':entry_id,
			   'enzyme':enz,
			   'roles':rles,
			   'compartments_reactions':new_enzyme_dict['cpts']}
	complexes_list.append(complex)
	update_complexes=True

print("+"*30)

if(updated_roles is True):
	with open(os.path.join(database_relative_path, "PlantSEED_Roles.json"),'w') as new_subsystem_file:
		json.dump(roles_list,new_subsystem_file,indent=4)

if(update_complexes is True):
	with open(os.path.join(database_relative_path, "PlantSEED_Complexes.json"),'w') as new_complex_file:
		json.dump(complexes_list,new_complex_file,indent=4)