#!/usr/bin/env python
import os,sys,json
import hashlib
# Open database
script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
database_relative_path = os.path.join(script_directory, "../../../", "Data/PlantSEED_v3/")
with open(os.path.join(database_relative_path, "PlantSEED_Roles.json")) as subsystem_file:
	roles_list = json.load(subsystem_file)

ged = dict() # global_enzyme_dict
exc_list = list() # to store excluded compartmentalized reactions
for entry in roles_list:
	if('abstract_enzyme' not in entry):
		continue

	enz = entry['abstract_enzyme']

	# special case of Spontaneous Reaction
	if(enz.lower() == 'spontaneous reaction'):
		# the entry always has a single spontaneous reaction
		# but as there's no enzyme, we need to distinguish 
		# between each one here
		enz = enz+"||"+entry['reactions'][0]

	if(enz not in ged):
		ged[enz]=dict()

	rle = entry['role']
	if(rle not in ged[enz]):
		ged[enz][rle]={'rxns':{},'rgts':[]}

	for rxn in entry['reactions']:
		if(rxn not in ged[enz][rle]['rxns']):
			ged[enz][rle]['rxns'][rxn]=list()

	if('compartmentalization' in entry):
		for lcz in entry['compartmentalization']:
			cpt = entry['compartmentalization'][lcz]['reaction']
			exc = entry['compartmentalization'][lcz]['exclude']

			for rxn in ged[enz][rle]['rxns']:
				if(cpt not in ged[enz][rle]['rxns'][rxn]):
					ged[enz][rle]['rxns'][rxn].append([cpt,lcz])
				
				rxn_cpt = rxn+"_"+cpt
				for kbase_id in entry['compartmentalization'][lcz]['kbase_ids']:
					if(rxn_cpt not in entry['compartmentalization'][lcz]['kbase_ids'][kbase_id]):
						print("WARNING: ",enz,rle,entry['compartmentalization'],rxn_cpt)
						pass
				
				# capture reactions that shouldn't be in model
				if(exc is True):
					reject = enz+"|"+rxn_cpt
					if(reject not in exc_list):
						exc_list.append(reject)

# checked to see if roles cross enzymes
# We're good
# red = dict() # roles_enzymes_dict
# for enz in ged:
# 	for rle in ged[enz]:
# 		if(rle not in red):
# 			red[rle]=list()
# 		if(enz not in red[rle]):
# 			red[rle].append(enz)

# The only ones that are linked to multiple "enzymes"
# are spontaneous reactions
# for rle in red:
# 	if(len(red[rle])>1):
# 		print(rle,red[rle])

# Checked to see if reactions cross enzymes
# xed = dict() # reactions_enzymes_dict
# for enz in ged:
# 	for rle in ged[enz]:
# 		for rxn in ged[enz][rle]:
# 			for cpt in ged[enz][rle][rxn]:
# 				rxn_cpt = rxn+"_"+cpt
# 				if(rxn_cpt not in xed):
# 					xed[rxn_cpt]=list()
# 				if(enz not in xed[rxn_cpt]):
# 					xed[rxn_cpt].append(enz)

# 	NB: yes there are a few reactions catalyzed by multiple enzymes
# for rxn in xed:
# 	if(len(xed[rxn])>1):
# 		print(rxn,xed[rxn])

global_complex_dict = dict()
for enz in ged:
	sorted_roles = sorted(list(ged[enz].keys()))
	sorted_rxn_cpts = list()
	cpts_rxns_exclude = dict()
	for rle in sorted_roles:
		for rxn in ged[enz][rle]['rxns']:
			for cpt,rgt in ged[enz][rle]['rxns'][rxn]:
				rxn_cpt = rxn+"_"+cpt
				if(rxn_cpt not in sorted_rxn_cpts):
					sorted_rxn_cpts.append(rxn_cpt)
				if(cpt not in cpts_rxns_exclude):
					cpts_rxns_exclude[cpt]={'reactions':[],
							 				'reagents':rgt,
							 				'exclude':False}
				if(rxn not in cpts_rxns_exclude[cpt]['reactions']):
					cpts_rxns_exclude[cpt]['reactions'].append(rxn)
				if(enz+"|"+rxn_cpt in exc_list):
					print(enz+"|"+rxn_cpt)
					cpts_rxns_exclude[cpt]['exclude']=True

	sorted_rxn_cpts = sorted(sorted_rxn_cpts)
	cpx_str = " / ".join([enz,"|".join(sorted_roles),"|".join(sorted_rxn_cpts)])
	kbase_id = 'PS_complex_' + hashlib.sha256(cpx_str.encode('utf-8')).hexdigest()[:6]
	while(kbase_id in global_complex_dict):
		print("Recurring for ",cpx_str)
		kbase_id = 'PS_complex_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]

	complex_dict = {'kbase_id':kbase_id,
				    'enzyme':enz,
					'roles':sorted_roles,
					'compartments_reactions':cpts_rxns_exclude}
	global_complex_dict[kbase_id]=complex_dict

global_complex_list = list()
for key in global_complex_dict:
	global_complex_list.append(global_complex_dict[key])

with open(os.path.join(database_relative_path, "PlantSEED_Complexes.json"),'w') as new_biochem_file:
	json.dump(global_complex_list,new_biochem_file,indent=4)
