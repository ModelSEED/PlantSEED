#!/usr/bin/env python
import datetime
import httpx
import time
import pickle
import copy
import sys
import os
import re
import json

############################
## Load Biochemistry
############################
# See if reactions are pickled otherwise fetch them
reactions_dict = dict()
if(os.path.isfile('Cache/MS_Rxns.pickle')):
	with open('Cache/MS_Rxns.pickle', 'rb') as rfh:
		reactions_dict = pickle.load(rfh)
else:
	print("Reactions Cache not found!")
	sys.exit(1)

updated_rxns_dict = {"RD":[],"GF":[],"UR":[],"PS":[],"CX":[]}
############################
## Load Additional Curation
############################

# A) Load Reaction Curation
# List of reactions for which their direction should be fixed as
# It differs from the biochemistry
curated_reactions_dict=dict()
direction_file = "../../../Data/PlantSEED_v3/Curated_Reaction_Directions_MSDv1.1.1.txt"
with open(direction_file) as rxn_fh:
	for line in rxn_fh.readlines():
		line=line.rstrip('\r\n')
		base_rxn,dir=line.split('\t')
		if(base_rxn in reactions_dict and reactions_dict[base_rxn]['is_obsolete']==1):
			if(base_rxn not in updated_rxns_dict['RD']):
				updated_rxns_dict['RD'].append(base_rxn)
			base_rxn = reactions_dict[base_rxn]['linked_reaction'].split(';')[0]
		curated_reactions_dict[base_rxn]=dir
with open(direction_file,'w') as rxn_fh:
	for rxn in sorted(curated_reactions_dict):
		rxn_fh.write(f"{rxn}\t{curated_reactions_dict[rxn]}\n")

# B) Load Gapfilling Curation
# This is a list of reactions in PlantSEED that are commonly
# made reversible as part of a gapfilling solution when they shouldn't be
# This is not necessary as part of a re-compilation, but if we ever need to use
# gapfilling to fix a new pathway, then we need this.
limited_gf_reactions_list=list()
gapfill_file = "../../../Data/PlantSEED_v3/Restricted_PlantSEED_Gapfilling_MSDv1.1.1.txt"
with open(gapfill_file) as gf_rxn_fh:
	for line in gf_rxn_fh.readlines():
		line=line.rstrip('\r\n')
		base_rxn=line
		if(base_rxn in reactions_dict and reactions_dict[base_rxn]['is_obsolete']==1):
			if(base_rxn not in updated_rxns_dict['GF']):
				updated_rxns_dict['GF'].append(base_rxn)
			base_rxn = reactions_dict[base_rxn]['linked_reaction'].split(';')[0]
		limited_gf_reactions_list.append(base_rxn)
with open(gapfill_file,'w') as gf_rxn_fh:
	gf_rxn_fh.write("\n".join(sorted(limited_gf_reactions_list)))

# C) Load unbalanced reactions to include
# The update to the biochemistry meant that a few reactions *became* unbalanced when
# they shouldn't have been.
# As of 12/01/20, there are two problematic compounds: THF and Stearoyl-ACP that need investigating
excepted_reactions_list=list()
unb_rxn_file = "../Template/Unbalanced_Reactions_to_Fix.txt"
with open(unb_rxn_file) as exc_rxn_fh:
	for line in exc_rxn_fh.readlines():
		line=line.rstrip('\r\n')
		base_rxn=line
		if(base_rxn in reactions_dict and reactions_dict[base_rxn]['is_obsolete']==1):
			if(base_rxn not in updated_rxns_dict['UR']):
				updated_rxns_dict['UR'].append(base_rxn)
			base_rxn = reactions_dict[base_rxn]['linked_reaction'].split(';')[0]
		excepted_reactions_list.append(base_rxn)
with open(unb_rxn_file,'w') as exc_rxn_fh:
	exc_rxn_fh.write("\n".join(sorted(excepted_reactions_list)))

############################
## Load PlantSEED
############################

#Load PlantSEED Subsystems, Roles, Reactions
subsystem_file = "../../../Data/PlantSEED_v3/PlantSEED_Roles.json"
with open(subsystem_file) as subsystem_fh:
	roles_list = json.load(subsystem_fh)

for entry in roles_list:
	if('reactions' not in entry):
		continue

	reactions = entry['reactions']
	for i in range(len(reactions)):
		base_rxn = reactions[i]
		if(base_rxn in reactions_dict and reactions_dict[base_rxn]['is_obsolete']==1):
			new_rxn = reactions_dict[base_rxn]['linked_reaction'].split(';')[0]
			
			if(base_rxn not in updated_rxns_dict['PS']):
				updated_rxns_dict['PS'].append(base_rxn)

			reactions[i] = new_rxn

			for cpt_id in entry['localization']:
				cpt = entry['localization'][cpt_id]
				if(base_rxn in cpt):
					cpt[new_rxn]=cpt[base_rxn]
					del(cpt[base_rxn])

			for cpt_id in entry['compartmentalization']:
				cpt = entry['compartmentalization'][cpt_id]
				for cpx in cpt['kbase_ids']:
					cpx_rxns = cpt['kbase_ids'][cpx]
					for j in range(len(cpx_rxns)):
						if(base_rxn in cpx_rxns[j]):
							cpx_rxns[j] = cpx_rxns[j].replace(base_rxn,new_rxn)
					cpt['kbase_ids'][cpx]=cpx_rxns
				entry['compartmentalization'][cpt_id]=cpt

with open(subsystem_file,'w') as subsystem_fh:
	json.dump(roles_list,subsystem_fh,indent=4)

complex_file = '../../../Data/PlantSEED_v3/Complex/Consolidated_PlantSEED_Complex_Curation.json'
with open(complex_file) as complex_fh:
	complex_dict = json.load(complex_fh)

	for complex_id in complex_dict:
		complex = complex_dict[complex_id]
		if(complex['reaction'] in reactions_dict and reactions_dict[complex['reaction']]['is_obsolete']==1):
			if(base_rxn not in updated_rxns_dict['CX']):
				updated_rxns_dict['CX'].append(base_rxn)

			new_reaction = reactions_dict[complex['reaction']]['linked_reaction'].split(';')[0]
			complex['reaction']=new_reaction
with open(complex_file,'w') as complex_fh:
	json.dump(complex_dict,complex_fh,indent=4)

for entry in updated_rxns_dict:
	print(entry,len(updated_rxns_dict[entry]))