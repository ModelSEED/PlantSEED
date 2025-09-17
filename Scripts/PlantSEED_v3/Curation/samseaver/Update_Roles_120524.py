#!/usr/bin/env python
import os,sys,json

if(len(sys.argv)<2 or os.path.isfile(sys.argv[1]) is False):
	print("Takes one argument, the path to and including roles file")
	sys.exit()

updated_roles_dict=dict()
add_dict=dict()
rem_dict=dict()
replace_dict=dict()
new_list=list()
with open(sys.argv[1]) as updates_file:
	print("opened file")
	for line in updates_file.readlines():
		line=line.strip('\r\n')
		tmp_lst=line.split('   ') # I switch this to be the size of three spaces instead because tab did not work
		print("what is this") #added for testing
		print(tmp_lst) #equivalent of one line in .tsv added for testing
		
		if(tmp_lst[1] == "UPDATE"): #updated_roles_dict
			replace_dict[tmp_lst[0]]=tmp_lst[2]

		if(tmp_lst[1] == "NEW"):
			new_list.append(tmp_lst[2])

		if(tmp_lst[1] == "ADD"): #add_dict
			print(tmp_lst[0] )
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


			
with open("/home/tesse044/Bio_Research/PlantSEED/Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
	roles_list = json.load(subsystem_file)

print(len(roles_list)) # roles_list has 935 lines, testing
# check for "new" roles first
for entry in roles_list:
	if(entry['role'] in new_list):
		print("Warning, New Role already present: "+entry['role'])
		sys.exit()
print("makes it here")
for new in new_list:
	roles_list.append({'role':new})


updated_roles=False
print(updated_roles) #makes it to this point I added this for testing
print((add_dict))
for entry in roles_list:
	updated_roles=False

	# Must change role name first if need to!
	if(entry['role'] in replace_dict):
		entry['role'] = replace_dict[entry['role']]
		updated_roles=True

	# Iterate through entries to add to role
					# print("what is in entry[role]")
	#print(entry['role'])
	if(entry['role'] in add_dict.keys()):
		print("FOUND") # added for testing
		for field in add_dict[entry['role']]:
			print(len(add_dict[entry['role']]))
			if(field not in entry['role']):
				entry[field]=list()

			for input in add_dict[entry['role']][field].keys():
				print("ADD",field,input)
				# Check to see if it's not there, and add it
				if(input not in entry[field]):
					entry[field].append(input)

				# Update localization
				if(field == 'features' and 'localization' in entry):

					for cpt in entry['localization']:
						
						if(add_dict[entry['role']][field][input] in entry['localization'][cpt]):
							entry['localization'][cpt][input] = entry['localization'][cpt][add_dict[entry['role']][field][input]]

				# Update compartmentalization
				if(field == 'reactions'):
					print("found reaction feild")
					for cpts in entry['compartmentalization']:
						if(cpts in add_dict[entry['role']][field][input]):
							tmpl_rxn = input+'_'+entry['compartmentalization'][cpts]['reaction']
							for complex in entry['compartmentalization'][cpts]['kbase_ids']:
								if(input not in entry['compartmentalization'][cpts]['kbase_ids'][complex]):
									entry['compartmentalization'][cpts]['kbase_ids'][complex].append(tmpl_rxn)

		updated_roles=True 
		print("updated role below") #for testing
		print(updated_roles) # for testing
	# Iterate through entries to remove from role
	if(entry['role'] in rem_dict):
		for field in rem_dict[entry['role']]:
			for input in rem_dict[entry['role']][field]:
				# Check to see if it is there and remove it
				if(input in entry[field]):
					entry[field].remove(input)

				if(field == 'features'):
					delete_cpts=list()
					for cpt in entry['localization']:
						if(input in entry['localization'][cpt]):
							del(entry['localization'][cpt][input])
						if(len(entry['localization'][cpt])==0):
							delete_cpts.append(cpt)

					for cpt in delete_cpts:
						del(entry['localization'][cpt])

		updated_roles=True
		print("made it")

	if(updated_role is True):
		if('curators' not in entry):
			entry['curators']=list()
		if ('ricon001' not in entry['curators']):
			entry['curators'].append('ricon001')
		if ('pelle283' not in entry['curators']):
			entry['curators'].append('pelle283')
		if('samseaver' not in entry['curators']):
			entry['curators'].append('samseaver')
		updated_roles=True

if(updated_roles is True):
	with open('/home/tesse044/Bio_Research/PlantSEED/Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
		json.dump(roles_list,new_subsystem_file,indent=4)
