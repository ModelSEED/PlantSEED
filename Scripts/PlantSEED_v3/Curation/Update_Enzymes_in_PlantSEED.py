#!/usr/bin/env python
import os,sys,json,copy

input_file = None
if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
	print("Takes one argument, the path to and including roles file")
	sys.exit()
else:
	input_file = sys.argv[1]

updated_roles_dict=dict()
add_dict=dict()
rem_dict=dict()
replace_dict=dict()
new_list=list()
key_dict=dict()
change_dict=dict()
assign_dict=dict()
with open(input_file) as updates_file:
	for line in updates_file.readlines():
		line=line.strip('\r\n')

		if(line.startswith('#')):
			continue

		tmp_lst=line.split('\t')
		# print(tmp_lst)

		enzyme = tmp_lst[0]
		action = tmp_lst[1].upper()

		# This action is reserved for changing the name of the functional role
		# So the code has to create a new entry in the file and remove the old one
		if(action == "UPDATE"):
			new_enzyme = tmp_lst[2]
			replace_dict[enzyme]=new_enzyme

		# The following actions are for changing data within an enzyme's entry
		
		# This action is reserved for adding a new (empty) field to the functional role
		# It should ideally be followed up with an ADD action
		if(action == "NEW"):
			new_list.append(enzyme)
			print("Warning: is this enzyme conserved!",enzyme)
                        
		# This action is reserved for adding new data to a field in the functional role
		# Some fields take a key-value pair to add to a dict,
		# while others take a single entry to append to a list
		if(action == "ADD"):
			field = tmp_lst[2]
			entry = tmp_lst[3]
			if(enzyme not in add_dict):
				add_dict[enzyme]=dict()
			if(field not in add_dict[enzyme]):
				add_dict[enzyme][field]=dict()
			add_dict[enzyme][field][entry]=1
			if(len(tmp_lst)>4):
				entry_key = tmp_lst[3]
				entry_value = tmp_lst[4]
				add_dict[enzyme][field][entry_key]=entry_value
		
		# This action is reserved for removing data from a field in the functional role
		if(action == "REMOVE"):
			field = tmp_lst[2]
			entry = tmp_lst[3]
			if(enzyme not in rem_dict):
				rem_dict[enzyme]=dict()
			if(field not in rem_dict[enzyme]):
				rem_dict[enzyme][field]=list()
			rem_dict[enzyme][field].append(entry)

		# This action is reserved for rekeying a key-value pair in a dict
		# At the present time, it's only reserved for localization and compartmentalization
		# If the localization is updated, then the entire compartmentalization entry will also be updated
		if(action == "RELOCATE"):
			field = tmp_lst[2]
			entry = tmp_lst[3]
			new_entry = tmp_lst[4]
			if(enzyme not in key_dict):
				key_dict[enzyme]=dict()
			if(field not in key_dict[enzyme]):
				key_dict[enzyme][field]=dict()
			key_dict[enzyme][field][entry]=new_entry

		# This action is if the value is a simple string. 
		# At the moment this is only for abstract_enzyme and include
		if(action == "CHANGE"):
			field = tmp_lst[2]
			entry = tmp_lst[3]
			if(enzyme not in change_dict):
				change_dict[enzyme]=dict()
			change_dict[enzyme][field]=entry

		# This is for the single value variables like include and type
		if(action == "ASSIGN"):
			field = tmp_lst[2]
			entry = tmp_lst[3]
			if(enzyme not in assign_dict):
				assign_dict[enzyme]=dict()
			assign_dict[enzyme][field]=entry

script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
database_relative_path = os.path.join(script_directory, "../../../", "Data/PlantSEED_v3/")
with open(os.path.join(database_relative_path, "PlantSEED_Roles.json")) as subsystem_file:
	roles_list = json.load(subsystem_file)

# check for "new" roles first
for entry in roles_list:
	if(entry['role'] in new_list):
		print("Warning, New Role already present: "+entry['role'])
		sys.exit()

default_role_dict = {'role':None,
					 'features':list(),
					 'reactions':list(),
					 'subsystems':list(),
					 'curators':list(),
					 'localization':dict(),
					 'publications':list(),
					 'classes':dict(),
					 'include':True,
					 'abstract_enzyme':''}

for new in new_list:
	new_role = copy.deepcopy(default_role_dict)
	new_role['role'] = new

	new_role['abstract_enzyme']=new.split(' (EC')[0]
	roles_list.append(new_role)

updated_roles=False
for entry in roles_list:
	updated_role=False

	# Must change role name first if need to!
	if(entry['role'] in replace_dict):
		entry['role'] = replace_dict[entry['role']]
		updated_role=True

	# Iterate through entries to add to role
	if(entry['role'] in add_dict):
		for field in add_dict[entry['role']]:
			if(field not in entry):
				entry[field]=list()

			for input in add_dict[entry['role']][field]:

				# Check to see if it's not there, and add it
				if(input not in entry[field]):
					entry[field].append(input)

				# Update localization if feature
				if(field == 'features'):
					if(add_dict[entry['role']][field][input]==1):
						print("Warning, no localization data added for feature: ",input)
					else:
						(cpt,code) = add_dict[entry['role']][field][input].split(':')
						if(cpt in entry['localization']):
							entry['localization'][cpt][input]=[code]
						else:
							entry['localization'][cpt]={input:[code]}

				# Update classes
				if(field == 'subsystems'):
					sys_cls = add_dict[entry['role']][field][input]
					if(sys_cls == "1"):
						print("Warning: class not included as extra field for subsystem: ",input)
					if('classes' not in entry):
						entry['classes'] = dict()
					if(sys_cls not in entry['classes']):
						entry['classes'][sys_cls] = dict()
					entry['classes'][sys_cls][input]=[]

				# Update compartmentalization
				if(field == 'reactions'):
					if(add_dict[entry['role']][field][input]==1):
						# print("No compartments specified for reaction: "+input)
						continue
					else:
						cpt = add_dict[entry['role']][field][input]
						if('localization' not in entry):
							entry['localization']=dict()
						if(cpt not in entry['localization']):
							entry['localization'][cpt]=dict()
						entry['localization'][cpt][input]=["Assumed"]

		updated_role=True

	if(entry['role'] in assign_dict):
		for field in assign_dict[entry['role']]:
			entry[field]=assign_dict[entry['role']][field]
		updated_role=True

	if(entry['role'] in key_dict):
		print(entry['role'])

		for field in key_dict[entry['role']]:

			for old_entry in key_dict[entry['role']][field]:
				new_entry = key_dict[entry['role']][field][old_entry]
				
				if(old_entry not in entry[field]):
					print("Warning, old entry not found in field: "+old_entry)
					continue

				entry[field][new_entry] = entry[field][old_entry]
				del(entry[field][old_entry])

				# Update compartmentalization
				if(old_entry in entry['compartmentalization']):
					new_hash = copy.deepcopy(entry['compartmentalization'][old_entry])
					new_hash['reaction'] = new_entry
					for kbid in new_hash['kbase_ids']:
						for rxn_idx in range(len(new_hash['kbase_ids'][kbid])):
							rxn = new_hash['kbase_ids'][kbid][rxn_idx]
							rxn = rxn.replace('_'+old_entry,'_'+new_entry)
							new_hash['kbase_ids'][kbid][rxn_idx] = rxn

					entry['compartmentalization'][new_entry] = new_hash
					del(entry['compartmentalization'][old_entry])
				updated_role=True

	# Iterate through entries to remove from role
	if(entry['role'] in rem_dict):
		for field in rem_dict[entry['role']]:
			for input in rem_dict[entry['role']][field]:
				# Check to see if it is there and remove it
				if isinstance(entry[field], list):
					entry[field].remove(input)
				elif isinstance(entry[field], dict):
					del entry[field][input]

				if(field == 'features'):
					delete_cpts=list()
					for cpt in entry['localization']:
						if(input in entry['localization'][cpt]):
							del(entry['localization'][cpt][input])
						if(len(entry['localization'][cpt])==0):
							delete_cpts.append(cpt)

					for cpt in delete_cpts:
						del(entry['localization'][cpt])

		updated_role=True

	if(entry['role'] in change_dict):
		for field in change_dict[entry['role']]:
			entry[field]=change_dict[entry['role']][field]

		updated_role=True

	if(updated_role is True):
		if('curators' not in entry):
			entry['curators']=list()

		# Curators must be using their github username as the immediate parent folder
		# of the TSV (e.g. .../Curation/Curators/<github_username>/<file>.tsv).
		# Using basename(input_directory) is robust to extra path levels above it.

		input_directory = os.path.dirname(os.path.abspath(input_file))
		curator = os.path.basename(input_directory)

		if(curator not in entry['curators']):
			entry['curators'].append(curator)
	
		updated_roles=True

if(updated_roles is True):
	with open(os.path.join(database_relative_path, "PlantSEED_Roles.json"),'w') as new_subsystem_file:
		json.dump(roles_list,new_subsystem_file,indent=4)
