#!/usr/bin/env python
import datetime
import httpx
import time
import pickle
import copy
import glob
import os
import re
import json

def fetch_biochemistry_data(url: str, pattern: str, branch: str):
    
	# Set the branch via the 'ref' query parameter
	params = { "ref": branch }

	# Set up headers, including the token for authentication
	headers = { "Accept": "application/vnd.github.v3+json" }

	# Make the API request
	with httpx.Client() as client:
		try:
			response = client.get(url, headers=headers, params=params)
			response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
			directory_contents = response.json()
		except httpx.HTTPStatusError as e:
			print(f"Error fetching directory contents: {e}")
		except httpx.RequestError as e:
			print(f"An error occurred during the request: {e}")

	compiled_pattern = re.compile(pattern)
	data_dict=dict()
	with httpx.Client(headers=headers, follow_redirects=True) as client:
		for item in directory_contents:
			# Check if the item is a file AND its name matches the regex pattern
			if item.get("type") == "file" and compiled_pattern.match(item.get("name", "")):
				download_url = item["download_url"]
		
				try:
					# The download_url points to the raw file, so no special GitHub headers are needed, 
					# but the Authorization header might be.
					response = client.get(download_url)
					response.raise_for_status()
                
					# The content is a raw string (the JSON text)
					raw_content = response.text
                
					# Parse the JSON string into a Python object (dictionary or list)
					file_data = json.loads(raw_content)
					for entry in file_data:
						data_dict[entry['id']]=entry

				except httpx.HTTPStatusError as e:
					print(f"   - ❌ Failed to download {file_name} (HTTP Error: {e.response.status_code})")
				except json.JSONDecodeError:
					print(f"   - ❌ Failed to parse {file_name} as JSON.")
				except Exception as e:
					print(f"   - ❌ An unexpected error occurred with {file_name}: {e}")
				
	return data_dict

#bioObj_ref = "/chenry/public/modelsupport/biochemistry/plantdefault.biochem" #PMS reference
biochem_ref = "48/1/5" #AppDev reference NB: doesn't work in production!

############################
## Load Additional Curation
############################

# A) Load Reaction Curation
# List of reactions for which their direction should be fixed as
# It differs from the biochemistry
curated_reactions_dict=dict()
with open("../../../Data/PlantSEED_v3/Curated_Reaction_Directions_MSDv1.1.1.txt") as rxn_fh:
	for line in rxn_fh.readlines():
		line=line.rstrip('\r\n')
		array=line.split('\t')
		curated_reactions_dict[array[0]]=array[1]

# B) Load Gapfilling Curation
# This is a list of reactions in PlantSEED that are commonly
# made reversible as part of a gapfilling solution when they shouldn't be
# This is not necessary as part of a re-compilation, but if we ever need to use
# gapfilling to fix a new pathway, then we need this.
limited_gf_reactions_list=list()
with open("../../../Data/PlantSEED_v3/Restricted_PlantSEED_Gapfilling_MSDv1.1.1.txt") as gf_rxn_fh:
	for line in gf_rxn_fh.readlines():
		line=line.rstrip('\r\n')
		limited_gf_reactions_list.append(line)

# C) Load Asymmetric transport
# The asymmetric transport is now encoded in the PlantSEED Biochemistry file.
# I'm leaving this note as it's an important distinction that may be lost.

# D) Load unbalanced reactions to include
# The update to the biochemistry meant that a few reactions *became* unbalanced when
# they shouldn't have been.
# As of 12/01/20, there are two problematic compounds: THF and Stearoyl-ACP that need investigating
excepted_reactions_list=list()
with open("Unbalanced_Reactions_to_Fix.txt") as exc_rxn_fh:
	for line in exc_rxn_fh.readlines():
		line=line.rstrip('\r\n')
		excepted_reactions_list.append(line)
print("Including unbalanced reactions: "+", ".join(excepted_reactions_list))

time_string = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %Hh %Mm %Ss'))
print("Loading biochemistry "+time_string)
############################
## Load Biochemistry
############################
msd_base_url = f"https://api.github.com/repos/ModelSEED/ModelSEEDDatabase/contents/Biochemistry"
# Pinned to a specific commit on ModelSEEDDatabase/dev so the generated
# template stays reproducible while Sam works on reversibility upstream.
# This is the commit immediately BEFORE 6a3813875f (2026-05-29 "Run
# Estimate_Reaction_Reversibility.py to refresh stored reversibility"),
# so reaction directions match what they were prior to that refresh.
# Bump this when ready to pick up newer biochemistry; setting it back to
# "dev" tracks the moving branch tip (and re-introduces unpinned drift).
MSD_PINNED_COMMIT = "465b7116c18ba99af83ee38589a30c32e69510f6"  # 2026-05-06
msd_branch = MSD_PINNED_COMMIT
print(f"WARNING: ModelSEED biochemistry pinned to {MSD_PINNED_COMMIT[:10]} "
      f"(2026-05-06) — NOT the dev branch tip. Update MSD_PINNED_COMMIT "
      f"in Generate_Core_ModelTemplate.py to refresh.")

print("Warning: Add MSD as submodule!")
if(os.path.isdir('Biochem_Cache') is False):
	os.mkdir('Biochem_Cache')

# See if reactions are pickled otherwise fetch them
reactions_dict = dict()
if(os.path.isfile('Biochem_Cache/MS_Rxns.pickle')):
	with open('Biochem_Cache/MS_Rxns.pickle', 'rb') as rfh:
		reactions_dict = pickle.load(rfh)
else:
	reaction_pattern = r"^reaction_.*\.json$"
	reactions_dict = fetch_biochemistry_data(msd_base_url,reaction_pattern,msd_branch)
	
	# Its important to use binary mode
	with open('Biochem_Cache/MS_Rxns.pickle', 'wb') as rfh:
		pickle.dump(reactions_dict,rfh)

print("Reactions: ",len(reactions_dict))

# See if compounds are pickled otherwise fetch them
compounds_dict=dict()
if(os.path.isfile('Biochem_Cache/MS_Cpds.pickle')):
	with open('Biochem_Cache/MS_Cpds.pickle', 'rb') as cfh:
		compounds_dict = pickle.load(cfh)
else:
	compound_pattern = r"^compound_.*\.json$"
	compounds_dict = fetch_biochemistry_data(msd_base_url,compound_pattern,msd_branch)
	print("Compounds: ",len(compounds_dict))
	for compound in compounds_dict:
		cpd_obj = compounds_dict[compound]

		# fix default values
		for key in ["charge","mass","deltag","deltagerr"]:
			if(cpd_obj[key] is None):
				cpd_obj[key] = 0.0

		if(cpd_obj['formula'] is None):
			cpd_obj['formula'] = 'R'

		template_compound_hash = { 'id':compound, 'name':cpd_obj["name"],
								   'abbreviation':cpd_obj["abbreviation"], 'aliases':[],
								   'formula':cpd_obj["formula"], 'isCofactor':0,
								   'defaultCharge':float(cpd_obj["charge"]), 'mass':float(cpd_obj["mass"]),
								   'deltaG':float(cpd_obj["deltag"]), 'deltaGErr':float(cpd_obj["deltagerr"]),
								   'compound_ref':biochem_ref+"/compounds/id/"+cpd_obj['id'] }
		compounds_dict[compound]=template_compound_hash

	# Its important to use binary mode
	with open('Biochem_Cache/MS_Cpds.pickle', 'wb') as cfh:
		pickle.dump(compounds_dict,cfh)

time_string = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %Hh %Mm %Ss'))
print("Biochemistry loaded "+time_string)

#Collect compartments: NB The location will change
compartments = dict()
with open("../../../Data/PlantSEED_v3/Compartments/PlantSEED_Compartments.json") as cpt_fh:
	compartments = json.load(cpt_fh)

############################
## Load PlantSEED
############################

#Load Core Subsystems
#Load PlantSEED Subsystems, Roles, Reactions
with open("../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
	roles_list = json.load(subsystem_file)

#Collect Compartmentalized Reactions
roles=dict()
roles_ids=dict()
roles_types=dict()
excluded_roles=list()
# features, include, type, role id are collected in roles file
for entry in roles_list:
	role = entry['role']
	if(role.lower() == 'spontaneous reaction'):
		# a Spontaneous role entry always has a single spontaneous reaction
		# but as there's no enzyme, we need to distinguish 
		# between each one here
		role = role+"||"+entry['reactions'][0]

	if(entry['include'] is False):
		excluded_roles.append(role)
		continue

	if('reactions' not in entry):
		continue

	# Skip vacuolar ATP synthase, for pumping protons into vacuole
	if("rxn08173" in entry["reactions"] and "v" in entry["localization"]):
		print("Skipping vacuolar ATP synthase")
		excluded_roles.append(role)
		continue

	# Skip ubiquinol oxidase for now
	# https://en.wikipedia.org/wiki/Alternative_oxidase
	# https://www.annualreviews.org/doi/full/10.1146/annurev-arplant-042110-103857
	# It allows the TCA cycle to continue via succinate dehydrogenase
	# without translocating protons and producing ATP, which causes problems with FBA
	if("rxn12494" in entry["reactions"]):
		print("Skipping alternative ubiquinol oxidase")
		excluded_roles.append(role)
		continue

	if('kbase_id' in entry and entry['kbase_id'].startswith('PS_role_')):
		roles_ids[role]=entry['kbase_id']
	else:
		print("Included role does not have KBase ID:",role)
		continue
	
	if(role not in roles):
		roles[role]=list()

	for ftr in entry['features']:
		if(ftr not in roles[role]):
			roles[role].append(ftr)

	roles_types[role]=entry['type']

########################################################
## Load PlantSEED Complexes
########################################################

#Load Core Subsystems
#Load PlantSEED Subsystems, Roles, Reactions
with open("../../../Data/PlantSEED_v3/PlantSEED_Complexes.json") as biochem_file:
	complex_list = json.load(biochem_file)

############################################################
## Subcomplex absorption
## ---------------------
## A role may carry an optional `subcomplex_of: <parent_complex_kbase_id>`
## flag indicating that it (and the complex it belongs to) is structurally
## a sub-assembly of a larger parent complex (e.g. Cytochrome b559's PsbE/PsbF
## are subunits of Photosystem II; the glycine cleavage T-protein is a
## subunit of the Glycine cleavage system). For any such role we want the
## ModelTemplate's GPR to AND-extend the parent's complexroles rather than
## offering the carve-out as an independent OR-joined complex.
##
## Per Sam Seaver 2026-06-02: do NOT let `subcomplex_of` influence complex-id
## generation; the carve-out complex keeps its own kbase_id and source entry.
## Only the template-generation output is collapsed.
##
## A complex is treated as a carve-out only when ALL of its roles point at
## the SAME parent; mixed `subcomplex_of` targets within one complex are
## warned and left alone.
############################################################

roles_by_name = {entry['role']: entry for entry in roles_list}
subcomplex_parent = {}        # carve_out_complex_id -> parent_complex_id
subcomplex_extra_roles = {}   # parent_complex_id -> [role names to inject]
for complex in complex_list:
	parents = set()
	for role_name in complex.get('roles', []) or []:
		entry = roles_by_name.get(role_name)
		if entry and entry.get('subcomplex_of'):
			parents.add(entry['subcomplex_of'])
	if len(parents) == 1:
		parent_id = next(iter(parents))
		subcomplex_parent[complex['kbase_id']] = parent_id
		subcomplex_extra_roles.setdefault(parent_id, [])
		for role_name in complex['roles']:
			if role_name not in subcomplex_extra_roles[parent_id]:
				subcomplex_extra_roles[parent_id].append(role_name)
	elif len(parents) > 1:
		print(f"WARN: complex {complex['kbase_id']} ({complex.get('enzyme')}) has roles with conflicting "
		      f"subcomplex_of targets {sorted(parents)} — leaving as standalone GPR")

if subcomplex_parent:
	print(f"Subcomplex absorption: {len(subcomplex_parent)} carve-out complex(es) will be "
	      f"AND-extended into their parents:")
	for carve, parent in sorted(subcomplex_parent.items()):
		print(f"  {carve} -> {parent}  (roles: {subcomplex_extra_roles[parent]})")

complexes=dict()
excluded_roles_complexes=list()

reactions_roles=dict()
reactions_types=dict()
reactions_cpts=dict()
reactions_stoich=dict()

for complex in complex_list:
	complex_id = complex['kbase_id']

	to_include = list()
	for role in complex['roles']:
		if(role in excluded_roles):
			to_include.append(False)
		elif(role.lower() == 'spontaneous reaction' and complex['enzyme'] in excluded_roles):
			to_include.append(False)
		else:
			to_include.append(True)

	if(len(to_include)==1 and to_include[0] is False):
		excluded_roles_complexes.append(' / '.join(complex['roles'])+' / '+complex_id)
		continue

	if(complex['roles'][0].lower()=='spontaneous reaction'):
		complex['roles']=[complex['enzyme']]

	if(complex_id not in complexes):
		complexes[complex_id]={'reactions':[],'roles':complex['roles']}

	for cpt_id in complex['compartments_reactions']:
		cpt = complex['compartments_reactions'][cpt_id]
		if(cpt['exclude'] is True):
			excluded_roles_complexes.append(' / '.join(complex['roles'])+' / '+complex_id+' / '+cpt_id)
			continue

		for rxn in cpt['reactions']:
			if('direction' in complex):
				curated_reactions_dict[rxn]=complex['direction']

			tmpl_rxn = rxn+"_"+cpt_id

			# These are stored for indexing compound stoichiometry
			# when generating the reagents below
			reactions_cpts[tmpl_rxn]=cpt['reagents']

			# For changing/removing/adding compounds.
			# Enzyme-wide overrides apply to every reaction the enzyme catalyses;
			# reaction_stoichiometry scopes an override to one reaction and wins
			# where both name the same compound.
			if('stoichiometry' in complex or 'reaction_stoichiometry' in complex):
				merged = dict(complex.get('stoichiometry',{}))
				merged.update(complex.get('reaction_stoichiometry',{}).get(rxn,{}))
				if(merged):
					reactions_stoich[tmpl_rxn]=merged

			for role in complex['roles']:
				if(role.lower() == 'spontaneous reaction'):
					# a Spontaneous role entry always has a single spontaneous reaction
					# but as there's no enzyme, we need to distinguish 
					# between each one here
					role = complex['enzyme']

				# for excluded roles in a complex that contains included roles
				if(role in excluded_roles):
					continue

				if(tmpl_rxn not in reactions_roles):
					reactions_roles[tmpl_rxn]=list()
				if(role not in reactions_roles[tmpl_rxn]):
					reactions_roles[tmpl_rxn].append(role)

				if(tmpl_rxn in reactions_types and reactions_types[tmpl_rxn] != roles_types[role]):
					print("AH: ",roles_types[role])
				reactions_types[tmpl_rxn]=roles_types[role]

			if(tmpl_rxn not in complexes[complex_id]['reactions']):
					complexes[complex_id]['reactions'].append(tmpl_rxn)

# Inject carve-out roles into their parent complex's role list so that the
# parent's complexroles AND-includes them. The carve-out complex's own
# entry still exists in `complexes`; it will be filtered out of any
# reaction's templatecomplex_refs where the parent is also present (below).
for parent_id, extra_roles in subcomplex_extra_roles.items():
	if parent_id not in complexes:
		print(f"WARN: subcomplex parent {parent_id} not found in complexes — "
		      f"carve-out roles {extra_roles} cannot be merged")
		continue
	for r in extra_roles:
		if r not in complexes[parent_id]['roles']:
			complexes[parent_id]['roles'].append(r)
			# Also extend the per-reaction role list for every reaction the parent owns.
			for tmpl_rxn in complexes[parent_id]['reactions']:
				reactions_roles.setdefault(tmpl_rxn, [])
				if r not in reactions_roles[tmpl_rxn]:
					reactions_roles[tmpl_rxn].append(r)

############################
## Begin Template Generation
############################

#Generate Template Roles
template_roles=list()
role_count=1
template_role_file = open("Template_Roles_Record.txt",'w')
for role in sorted(roles):
	role_hash = { 'id':roles_ids[role], 'name':role, 'source':'PlantSEED',
					'aliases':[], 'features':sorted(roles[role]) }

	template_roles.append(role_hash)
	template_role_file.write(role_hash['id']+"\t"+role+"\n")

#Generate TemplateComplex and TemplateComplexRole
template_complexes=list()
template_reactions_complexes=dict()
rca_fh = open("Reaction_Complex_Assignments.txt", 'w');
for complex in sorted(complexes.keys()):
	complex_hash = { 'id' : complex,
					'name' : "", 'reference' : "",
					'source' : "PlantSEED",
					'confidence' : 1.0,
					'complexroles' : [] }
	if('roles' not in complexes[complex]):
		print("Missing Roles",complex,complexes[complex])
	for role in sorted(complexes[complex]['roles']):
		if(role not in roles_ids):
			print("Complexed role excluded:",role)
			continue
		
		complex_role_hash = { 'templaterole_ref' : "~/roles/id/"+roles_ids[role],
							'optional_role' : 0,
							'triggering' : 1 }

		complex_hash['complexroles'].append(complex_role_hash)
		rca_fh.write("\t".join(["|".join(complexes[complex]['reactions']),complex,roles_ids[role],role,"|".join(sorted(roles[role]))])+"\n")
	
	template_complexes.append(complex_hash)

	# Creating lookup for linking reactions to complexes later
	for template_reaction in complexes[complex]['reactions']:
		if(template_reaction not in template_reactions_complexes):
			template_reactions_complexes[template_reaction]=list()
		template_reactions_complexes[template_reaction].append(complex)

# Drop carve-out complexes from any reaction whose parent is also a complex
# for that reaction. The carve-out is then linked only to reactions the parent
# does NOT share (if any), preserving its independent GPR where it stands alone.
for tmpl_rxn, cpx_list in template_reactions_complexes.items():
	present = set(cpx_list)
	filtered = []
	for c in cpx_list:
		if c in subcomplex_parent and subcomplex_parent[c] in present:
			continue
		filtered.append(c)
	template_reactions_complexes[tmpl_rxn] = filtered

rca_fh.close()

# Generate TemplateReactions
template_reactions = list()

# NB: I'm using the empty reaction as a default reaction ref as it doesn't really affect anything
# But I need to double-check how reconstruct_plant_metabolism in plant_fbaImpl.py fetches
# biochemistry data

default_template_reaction = { 'id':'rxn14003_c', 'name':'',
							'templatecompartment_ref':"~/compartments/id/c",
							'reaction_ref':biochem_ref+"/reactions/id/"+"rxn14003", #base_reaction,
							'type':"universal",
							'direction':'=',
							'GapfillDirection':'=',
							'maxforflux':0.0, 'maxrevflux':0.0,
							'templateReactionReagents':[], 'templatecomplex_refs':[] }

check_tpl_cpt_dict = dict()
template_compartments = list()

check_tpl_cpd_dict = dict()
template_compounds = list()

check_tpl_cpcpd_dict = dict()
template_compcompounds = list()

excluded_rxns_fh = open("Excluded_Reactions.txt","w")
# De novo reactions are emitted last, so a curated reaction never precedes the
# database reactions in creating shared compcompounds. Charge no longer depends
# on this -- every compcompound takes the compound record's value -- but keeping
# the order stable keeps the emitted compcompound list stable too.
def _emit_order(tmpl_rxn):
	return (tmpl_rxn.split('_')[0] not in reactions_dict, tmpl_rxn)

for template_reaction in sorted(reactions_roles, key=_emit_order):

	[base_reaction,reaction_cpt]=template_reaction.split('_')

	# De novo reactions: curation asserts the step exists, ModelSEED has no entry.
	# Used for transport the network requires but the biochemistry does not carry
	# -- eight of the nine glucosinolate transport compounds have no transport
	# reaction anywhere in ModelSEED. The curator supplies the whole stoichiometry
	# through CPX_ADD, so a complete override IS the reaction definition rather
	# than a patch on top of one. Nothing else about such a reaction can be looked
	# up, so name, direction and status are all defaulted here.
	de_novo = base_reaction not in reactions_dict
	if(de_novo and template_reaction not in reactions_stoich):
		excluded_rxns_fh.write("Skipping unknown reaction: "+base_reaction+
							   "\tnot in ModelSEED and no curator stoichiometry\n")
		continue

	if(de_novo is False and reactions_dict[base_reaction]['is_obsolete'] == 1):
		print("Obsolete: ",base_reaction,": ",reactions_dict[base_reaction]['definition'])

	# Skip unbalanced reactions.
	#
	# The ModelSEED 'status' string is written when a reaction is deposited and is
	# never recomputed, so it can disagree with the reaction's own formulas in the
	# same commit. It is therefore not authoritative for reactions PlantSEED itself
	# modifies: a curator stoichiometry override is an assertion that the reaction
	# balances *as built*, and the reaction is admitted on that basis whatever the
	# deposited status says. Those assertions are audited after the fact by
	# Check_Template_Reaction_Balance.py, which recomputes balance from the generated
	# template using ModelSEEDDatabase's own BiochemPy.balanceReaction.
	#
	# Unbalanced_Reactions_to_Fix.txt is now only for reactions we admit *without*
	# fixing them -- genuine upstream breakage waved through deliberately.
	curator_modified = template_reaction in reactions_stoich
	if(de_novo is False and curator_modified is False and \
	   base_reaction not in excepted_reactions_list and \
	   (base_reaction not in reactions_dict or \
	 	('OK' not in reactions_dict[base_reaction]['status'] and \
			reactions_dict[base_reaction]['status'].startswith('CI:') is False))):
		excluded_rxns_fh.write("Skipping unbalanced reaction: "+base_reaction+"\t"+reactions_dict[base_reaction]['status']+"\n")
		continue

	if(de_novo is False and curator_modified is True and base_reaction in reactions_dict and \
	   'OK' not in reactions_dict[base_reaction]['status'] and \
	   reactions_dict[base_reaction]['status'].startswith('CI:') is False):
		print("INFO: "+template_reaction+": admitted on curator stoichiometry override "
			  "(deposited status "+reactions_dict[base_reaction]['status']+")")

	template_reaction_hash = copy.deepcopy(default_template_reaction)
	template_reaction_hash['id']=template_reaction
	template_reaction_hash['name']=('De novo: '+base_reaction) if de_novo \
								   else reactions_dict[base_reaction]['name']
	template_reaction_hash['templatecompartment_ref']="~/compartments/id/"+reaction_cpt

	#determine reaction type (indicates conservation)
	template_reaction_hash['type'] = reactions_types[template_reaction]
	
	#determine reaction direction
	direction = "="
	if(de_novo is False and reactions_dict[base_reaction]['reversibility'] != "?"):
		direction = reactions_dict[base_reaction]['reversibility']
	
	if(base_reaction in curated_reactions_dict):
		direction = curated_reactions_dict[base_reaction]
	template_reaction_hash['direction']=direction

	gapfilling_direction = "="
	if(base_reaction in limited_gf_reactions_list):
		gapfilling_direction = direction
	template_reaction_hash['GapfillDirection']=gapfilling_direction

	# Curator stoichiometry overrides for this enzyme, if any. Two accepted forms:
	#   flat   {cpd: "3"}                                  (legacy, hand-written)
	#   nested {cpd: {"coefficient": "3", "compartment": "d"}}   (CPX_ADD)
	# A coefficient of 0 removes the reagent; a compound not already in the
	# database reaction is ADDED (see the second pass below).
	# Keys are "cpd" (the reaction's first compartment) or "cpd@cpt" (that
	# compartment specifically). The same compound may appear under several
	# compartments — that is how a proton pump is expressed (H+ -4 in d, +4 in y),
	# so a second compartment must never overwrite the first.
	rxn_stoich_raw = reactions_stoich.get(template_reaction, {})
	rxn_stoich = {}
	for _k, _v in rxn_stoich_raw.items():
		_cpd, _, _cpt = _k.partition('@')
		# legacy nested form {"coefficient": x, "compartment": y} still read
		if isinstance(_v, dict):
			_cpt = _v.get('compartment') or _cpt
			_v = _v.get('coefficient')
		rxn_stoich[(_cpd, _cpt or None)] = float(_v)
	consumed = set()

	# Add reagents. A de novo reaction has no database entry to draw from: every
	# reagent arrives through the override, handled by the second pass below.
	for rgt in ([] if de_novo else reactions_dict[base_reaction]['stoichiometry']):
		# (coefficient,compound,gen_cpt,index,name)=entry.split(":")

		# Update the stoichiometry first of all. Prefer an override that names
		# this reagent's own compartment; fall back to the unqualified key.
		_this_cpt = reactions_cpts[template_reaction][rgt['compartment']]
		for _key in ((rgt['compound'], _this_cpt), (rgt['compound'], None)):
			if(_key in rxn_stoich):
				rgt['coefficient'] = rxn_stoich[_key]
				consumed.add(_key)
				break

		# if new stoichiometry is zero, then this means to remove the reagent
		if(rgt['coefficient'] == 0):
			continue

		# The generic compartment is an index
		# The reaction compartments (reaction_cpts) generally consist of one compartment
		#    so the index is 0
		# but in the case of a transporter, the reaction can have multiple compartments
		#    so the index may be 0, 1, or even 2 in rare cases
		rgt_cpt=reactions_cpts[template_reaction][rgt['compartment']]

		# Check and extend list of template compartments
		if(rgt_cpt not in check_tpl_cpt_dict):
			check_tpl_cpt_dict[rgt_cpt]=1
			template_compartments.append(compartments[rgt_cpt])

		# Check and extend list of template compounds
		if(rgt['compound'] not in check_tpl_cpd_dict):
			check_tpl_cpd_dict[rgt['compound']]=1
			template_compounds.append(compounds_dict[rgt['compound']])

		# Check and extend list of template compcompounds
		comp_compound = rgt['compound']+"_"+rgt_cpt
		if(comp_compound not in check_tpl_cpcpd_dict):
			check_tpl_cpcpd_dict[comp_compound]=1

			# Charge comes from the compound record, never from rgt['charge'].
			# reaction_*.json denormalises charge/formula/name into every reagent,
			# but nothing in ModelSEED reads that copy back -- parseStoich rebuilds
			# the reagent array from Compounds_Dict every time -- so it is never
			# refreshed. 13,569 of 262,517 reagent entries have drifted, and in
			# 13,540 of those the embedded formula still matches the compound, so
			# it is the charge alone that is stale rather than a different species.
			# Reading it gave a compound two different charges depending on which
			# reaction happened to create its compcompound first.
			comp_compound_hash = { 'id':comp_compound,
								   'charge':float(compounds_dict[rgt['compound']]['defaultCharge']),
								   'maxuptake':0.0,
								   'templatecompound_ref':"~/compounds/id/"+rgt['compound'],
								   'templatecompartment_ref':"~/compartments/id/"+rgt_cpt }

			template_compcompounds.append(comp_compound_hash)

		rxn_rgt_hash = { 'templatecompcompound_ref' : "~/compcompounds/id/"+comp_compound,
						 'coefficient' : float(rgt['coefficient']) }
		template_reaction_hash['templateReactionReagents'].append(rxn_rgt_hash)

	# Second pass: ADD reagents the curator specified that the database reaction
	# does not contain. Only the first pass can rescale or drop an existing
	# reagent; anything left unconsumed here is a genuine addition.
	for _key in [k for k in rxn_stoich if k not in consumed]:
		add_cpd, want_cpt = _key
		coef = rxn_stoich[_key]
		if(coef == 0):
			# "remove" on a compound that was never in the reaction — nothing to do
			continue
		if(add_cpd not in compounds_dict):
			print(f"WARNING: {template_reaction}: cannot add {add_cpd} — not in the biochemistry")
			continue
		reagent_cpts = reactions_cpts[template_reaction]
		if(want_cpt is None):
			# Default to the reaction's first compartment. For a transporter the
			# two sides are materially different, so say so rather than guess quietly.
			rgt_cpt = reagent_cpts[0]
			if(len(reagent_cpts) > 1):
				print(f"WARNING: {template_reaction} is a transporter ({reagent_cpts}); "
					  f"added compound {add_cpd} defaulted to compartment '{rgt_cpt}' — "
					  f"give CPX_ADD an explicit compartment column if that is wrong")
		elif(de_novo):
			# The override IS the reaction, so it also defines which compartments
			# the reaction spans -- there is no database entry to check against.
			rgt_cpt = want_cpt
		elif(want_cpt in reagent_cpts):
			rgt_cpt = want_cpt
		else:
			print(f"WARNING: {template_reaction}: requested compartment '{want_cpt}' for "
				  f"{add_cpd} is not among the reaction's compartments ({reagent_cpts}) — skipped")
			continue

		if(rgt_cpt not in check_tpl_cpt_dict):
			check_tpl_cpt_dict[rgt_cpt]=1
			template_compartments.append(compartments[rgt_cpt])
		if(add_cpd not in check_tpl_cpd_dict):
			check_tpl_cpd_dict[add_cpd]=1
			template_compounds.append(compounds_dict[add_cpd])
		comp_compound = add_cpd+"_"+rgt_cpt
		if(comp_compound not in check_tpl_cpcpd_dict):
			check_tpl_cpcpd_dict[comp_compound]=1
			template_compcompounds.append({ 'id':comp_compound,
				'charge':float(compounds_dict[add_cpd].get('defaultCharge', 0) or 0), 'maxuptake':0.0,
				'templatecompound_ref':"~/compounds/id/"+add_cpd,
				'templatecompartment_ref':"~/compartments/id/"+rgt_cpt })
		template_reaction_hash['templateReactionReagents'].append(
			{ 'templatecompcompound_ref' : "~/compcompounds/id/"+comp_compound,
			  'coefficient' : float(coef) })
		print(f"INFO: {template_reaction}: added reagent {add_cpd} "
			  f"({coef}) in compartment '{rgt_cpt}'")

	# Add complexes
	if(template_reaction in template_reactions_complexes):
		for complex in sorted(template_reactions_complexes[template_reaction]):
			complex_string = "~/complexes/id/"+complex
			template_reaction_hash['templatecomplex_refs'].append(complex_string)

	########################################################################
	# This is for printing the reaction with two distinct protein complexes
	# print(template_reaction_hash['id'])
	if(template_reaction_hash['id'] == "rxn00533_d"):
		for cpx_ref in template_reaction_hash['templatecomplex_refs']:
			cpx_id = cpx_ref.split("/")[-1]
			for complex in template_complexes:
				if(complex['id'] == cpx_id):
					for role_ref in complex['complexroles']:
						role_id = role_ref['templaterole_ref'].split('/')[-1]
						for role in template_roles:
							if(role['id'] == role_id):
								#print(template_reaction_hash['id'],cpx_id,role_id,role['name'],role['features'])
								pass
	########################################################################

	########################################################################
	# The thylakoid proton pumps (PSII rxn20632, cytochrome b6-f rxn20595) used
	# to be modified here. They are now curator-authored, in
	# Curators/samseaver/thylakoid_proton_pumps_260917/proton_pumps.tsv, and
	# carried on the complexes as compound@compartment stoichiometry overrides.
	# See the CPX_ actions in plantseed_curation.

	# The BCAT3 generic-compound swaps and the Methylthioalkylmalate
	# dehydrogenase NAD fix used to be hardcoded here. They are now
	# curator-authored, in
	# Curators/samseaver/template_reaction_mods_260917/glucosinolate_generics.tsv.
	#
	# A third block replaced generic hemoproteins with flavins in rxn53279.
	# That reaction is on no role and so never reaches the template — the block
	# was dead code and has been dropped rather than migrated.

	template_reactions.append(template_reaction_hash)

########################################################################
# Transport is admitted on the metabolites, not on the annotation.
#
# A transporter earns its place if the compound it moves is actually used on
# both ends of the journey, or if it is a dead end that has to get out. The
# gene is irrelevant: 91 of the 191 transporter roles carry no Arabidopsis
# feature, and gating on that would delete uptake the network depends on.
#
# Two clauses, applied to the compound(s) that actually cross a membrane:
#
#   bridge     the compound is metabolised in >= 2 compartments and at least
#              one of them is an endpoint of this transporter. Cytosol is the
#              hub -- 280 of 288 transporters touch it -- so a compound living
#              in plastid and mitochondrion needs both c-legs even though it
#              never reacts in the cytosol itself.
#   byproduct  the compound is produced at an endpoint and consumed nowhere in
#              the network. It still has to leave, or the reaction making it
#              stalls at steady state.
#
# EXEMPT_CPTS have no internal metabolism, so no metabolite can ever "be
# metabolised" there and the rule could never admit them: the thylakoid lumen
# (y) and mitochondrial intermembrane space (j) exist only for proton pumps,
# and the extracellular compartment (e) is the medium boundary.
#
# The roles stay 'universal' and so do the reactions. A transporter really is
# universal in the sense that matters -- every organism has one -- so the flag
# is not the place to express "this particular model does not need it". That
# judgement is made here, on the metabolites, and the extraneous ones simply are
# not emitted. Gene presence is deliberately not consulted: 91 of the 191
# transporter roles carry no Arabidopsis feature, and gating on that would
# delete uptake the network depends on.
EXEMPT_CPTS = {'y','j','e'}

# Dead-end byproducts given an explicit drain where they are produced, so they
# do not depend on a transport chain to leave. Both are made by one reaction and
# consumed by nothing anywhere.
BYPRODUCT_DRAINS = {'cpd00204':'d',   # CO, from thiC (rxn20643)
					'cpd02701':'m'}   # S-adenosyl-4-methylthio-2-oxobutanoate, from rxn02312

def _cpt_of(ref):
	return ref.split('/')[-1].rsplit('_',1)[1]
def _cpd_of(ref):
	return ref.split('/')[-1].rsplit('_',1)[0]

# biomass is added by Add_ModelTemplate_Biomass.py, after this script runs, so
# read its component list straight from the data file. Without it every
# biomass-only metabolite looks unmetabolised and its transporters are dropped.
biomass_cpds = set()
with open("../../../Data/PlantSEED_v3/Biomass/PlantSEED_Biomass.txt") as bio_fh:
	for line in bio_fh:
		line = line.strip('\r\n')
		if(line == "" or line[0] in (' ','#')):
			continue
		array = line.split("\t")
		biomass_cpds.add((array[1], array[2]))

def _is_transport(rxn):
	return len({_cpt_of(r['templatecompcompound_ref']) for r in rxn['templateReactionReagents']}) > 1

metabolised = dict()
produced    = dict()
consumed    = dict()
for rxn in template_reactions:
	if(_is_transport(rxn)):
		continue
	reversible = rxn.get('direction') == '='
	for rgt in rxn['templateReactionReagents']:
		cpd_id = _cpd_of(rgt['templatecompcompound_ref'])
		cpt_id = _cpt_of(rgt['templatecompcompound_ref'])
		metabolised.setdefault(cpd_id,set()).add(cpt_id)
		if(rgt['coefficient'] > 0 or reversible):
			produced.setdefault(cpd_id,set()).add(cpt_id)
		if(rgt['coefficient'] < 0 or reversible):
			consumed.setdefault(cpd_id,set()).add(cpt_id)
for cpd_id,cpt_id in biomass_cpds:
	metabolised.setdefault(cpd_id,set()).add(cpt_id)
	consumed.setdefault(cpd_id,set()).add(cpt_id)

def _crossing(rxn):
	"""compounds that actually change compartment in this reaction"""
	seen = dict()
	for rgt in rxn['templateReactionReagents']:
		seen.setdefault(_cpd_of(rgt['templatecompcompound_ref']),set()).add(
			_cpt_of(rgt['templatecompcompound_ref']))
	return {c:k for c,k in seen.items() if len(k) > 1}

kept_reactions = list()
dropped_transporters = list()
for rxn in template_reactions:
	if(_is_transport(rxn) is False):
		kept_reactions.append(rxn)
		continue
	cpts = {_cpt_of(r['templatecompcompound_ref']) for r in rxn['templateReactionReagents']}
	if(cpts & EXEMPT_CPTS):
		rxn['type'] = 'universal'   # belt and braces: these must never be gene-gated
		kept_reactions.append(rxn)
		continue
	crossing = _crossing(rxn)
	admitted = None
	for cpd_id,cpd_cpts in crossing.items():
		where = metabolised.get(cpd_id,set())
		if(cpd_cpts & where and len(where) > 1):
			admitted = 'bridge'
			break
		if(cpd_cpts & produced.get(cpd_id,set()) and not consumed.get(cpd_id,set())):
			admitted = 'byproduct'
			break
	if(admitted is None):
		dropped_transporters.append((rxn['id'], sorted(crossing.keys()), sorted(cpts)))
		continue
	rxn['type'] = 'universal'
	kept_reactions.append(rxn)

print("Transporters: kept "+str(len(kept_reactions)-sum(1 for r in kept_reactions if _is_transport(r) is False))
	  +", dropped "+str(len(dropped_transporters)))
with open("Excluded_Transporters.txt","w") as exc_fh:
	for rxn_id,cpds,cpts in sorted(dropped_transporters):
		exc_fh.write(rxn_id+"\t"+",".join(cpds)+"\t"+"|".join(cpts)+"\n")
template_reactions = kept_reactions

# explicit drains for the dead-end byproducts
for cpd_id,cpt_id in sorted(BYPRODUCT_DRAINS.items()):
	comp_compound = cpd_id+"_"+cpt_id
	if(comp_compound not in check_tpl_cpcpd_dict):
		continue
	drain_hash = copy.deepcopy(default_template_reaction)
	drain_hash['id'] = "drain_"+cpd_id+"_"+cpt_id
	drain_hash['name'] = "Byproduct drain: "+compounds_dict[cpd_id]['name']
	drain_hash['templatecompartment_ref'] = "~/compartments/id/"+cpt_id
	drain_hash['type'] = 'universal'
	drain_hash['direction'] = '>'
	drain_hash['GapfillDirection'] = '>'
	drain_hash['templateReactionReagents'] = [
		{'templatecompcompound_ref':"~/compcompounds/id/"+comp_compound,'coefficient':-1.0}]
	print("Byproduct drain: "+drain_hash['id']+" ("+compounds_dict[cpd_id]['name']+")")
	template_reactions.append(drain_hash)

#Populate model_template dictionary
model_template=dict()
model_template={ 'id' : "Plant",
				'domain' : "Plant",
				'name' : "Plant",
				'type' : "GenomeScale",
				'biochemistry_ref' : biochem_ref,
				
				'compartments' : sorted(template_compartments, key = lambda cpt:cpt['id']),
				'compounds' : sorted(template_compounds, key = lambda cpd:cpd['id']), 
				'compcompounds' : sorted(template_compcompounds, key = lambda ccpd:ccpd['id']),
				
				'reactions' : template_reactions, 
				'roles' : template_roles, 
				'complexes' : template_complexes, 
				
				'biomasses' : [],
				'pathways' : []}

#Save Template
with open("PlantSEED_Neutral_Template.json",'w') as ps_tmpl_fh:
	json.dump(model_template,ps_tmpl_fh,indent=4)
time_string = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %Hh %Mm %Ss'))
print("Template generated"+time_string)
