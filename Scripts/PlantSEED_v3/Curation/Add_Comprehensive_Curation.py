#!/usr/bin/env python
import os,sys,json
import glob
import itertools

def process_fasta(fasta_file):
	sequences=dict()

	file_handle = open(fasta_file,'r')
	# alternate header and sequence
	fasta_iter = (x[1] for x in itertools.groupby(file_handle, lambda line: line[0] == ">"))
	for header in fasta_iter:
		# drop the ">"
		header = next(header)[1:].strip()

		# join all sequence lines to one.
		seq = "".join(s.strip() for s in next(fasta_iter))

		fasta_header=""
		try:
			fasta_header, fasta_description = header.split(' ', 1)
		except:
			fasta_header = header
			fasta_description = None

		seq = seq.upper()
		sequences[fasta_header]=seq

	return sequences

if(len(sys.argv)<2 or os.path.isdir(sys.argv[1]) is False):
	print("Takes one argument, the path to and including the curation folder")
	sys.exit()

cur_folder = sys.argv[1]
print("Parsing folder: "+cur_folder)

file_root = os.path.dirname(__file__)
db_file=os.path.join(file_root,"../../../Data/PlantSEED_v3/PlantSEED_Roles.json")
with open(db_file) as subsystem_file:
	roles_list = json.load(subsystem_file)

roles_dict = dict()
rxns_dict  = dict()
ftrs_dict  = dict()
pubs_dict  = dict()

# Adding roles to roles_dict and spontaneous_reactions
spontaneous_reactions = list()
for entry in roles_list:
	roles_dict[entry['role']]=entry
	if(entry['role'] == 'Spontaneous Reaction'):
		for reaction in entry['reactions']:
			if(reaction not in spontaneous_reactions):
				spontaneous_reactions.append(reaction)
	rxns_dict[entry['role']] = entry['reactions']
	ftrs_dict[entry['role']] = entry['features']
	pubs_dict[entry['role']] = entry['publications']

############################################################
# As it stands, the data is now curated in multiple files:
# 1) The main pathway file: *-enzymes
# 2) Pathway flow, linking enzymes in succession: *-pathway-flow
# 3) Predicted genes as derived from protein families: *-predicted-genes
# 4) Fasta file containing protein sequences: *-fasta-files
# NB: At time of writing we will integrate pathway-flow at another date

############################################################
# Here we collect the predicted gene identifiers
predicted_genes_dict=dict()
search_path = os.path.join(cur_folder,"*-predicted-genes")
for predgenes_file in glob.glob(search_path):
	with open(predgenes_file) as predgenes_file_handle:
		for line in predgenes_file_handle.readlines():
			line=line.strip('\r\n')
			(gene,prediction,psi)=line.split('\t')
			gene = "Uniprot||"+gene
			#print(gene)
			if(gene not in predicted_genes_dict):
				predicted_genes_dict[gene]=dict()
			predicted_genes_dict[gene][prediction]=psi

############################################################
# Here we collect the protein sequences
updated_protein_sequences_dict=dict()
search_path = os.path.join(cur_folder,"*-fasta-files")
for protseq_file in glob.glob(search_path):
	protein_sequences_dict = process_fasta(protseq_file) #protseq_dict
	# print(protein_sequences_dict)
	updated_protein_sequences_dict = dict()
	for fasta_ID in protein_sequences_dict:
		uniprot_ID = fasta_ID.split('|')[1]
		uniprot_ID = "Uniprot||"+uniprot_ID
		# print(fasta_ID,fasta_ID.split('|'),fasta_ID.split('|')[1],uniprot_ID)
		updated_protein_sequences_dict[uniprot_ID]=protein_sequences_dict[fasta_ID]
	# print(updated_protein_sequences_dict)
		#del(protein_sequences_dict[fasta_ID])

############################################################
# Here we process the main pathway file
# The main pathway file has these columns, in order:
# 0: reaction
# 1: functional role
# 2: feature
# 3: publication
# 4: subsystem
# 5: class
# 6: pathway
# 7: localization
# 8: cofactors
# 9: homomers
# 10: activate  
# 11: type (universal|conditional)
# 12: curator

new_complex_rxns_dict = dict()

search_path = os.path.join(cur_folder,"*-enzymes")
for pwy_file in glob.glob(search_path):
	with open(pwy_file) as pwy_file_handle:
		for line in pwy_file_handle.readlines():
			if(line.startswith('reaction')):
				continue

			line=line.strip('\r\n')
			tmp_lst = line.split('\t')
			rxn = tmp_lst[0]
			role= tmp_lst[1]
			ftr = tmp_lst[2]
			pub = tmp_lst[3]
			ss  = tmp_lst[4]
			cls = tmp_lst[5]
			pwys = tmp_lst[6]
			loc = tmp_lst[7]
			cof = tmp_lst[8]
			hom = tmp_lst[9]
			inc = tmp_lst[10]
			typ = tmp_lst[11]
			cur = tmp_lst[12]

			new_role = False
			if(role not in roles_dict):
				new_role = True
			elif(role == 'Spontaneous Reaction'):
				if(rxn not in spontaneous_reactions):
					new_role = True

			####################################
			# UPDATE EXISTING ROLE
			if(new_role is False):
				print("Existing Role\t" + role)

				# Convert rxn or ftr to list if string
				if(isinstance(rxns_dict[role], str)):
					rxns_dict[role] = rxns_dict[role].split()
				if(isinstance(ftrs_dict[role], str)):
					ftrs_dict[role] = ftrs_dict[role].split()

				# Split rxn and ftr if possible
				# Otherwise turn string into list
				if(';' in rxn): rxn = rxn.split(';')
				else: rxn = rxn.split()
				if(';' in ftr): ftr = ftr.split(';')
				else: ftr = ftr.split()
				if(',' in pub): pub = pub.split(',')
				else: pub = pub.split()

				# Find index of role
				for i in range(len(roles_list)):
					if(roles_list[i]['role'] == role): index = i

				####################################
				# New reaction
				if(not set(rxn).issubset(set(rxns_dict[role]))):
					for entry in rxn:
						if entry not in rxns_dict[role]:
							roles_list[index]['reactions'].append(entry)
							print("\t\t  new reaction:\t" + entry)

				for entry in rxn:
					if(entry not in new_complex_rxns_dict):
						new_complex_rxns_dict[entry]=list()
					if(role not in new_complex_rxns_dict[entry]):
						new_complex_rxns_dict[entry].append(role)

				####################################
				# New feature
				if(not set(ftr).issubset(set(ftrs_dict[role]))):
					for entry in ftr:
						if entry not in ftrs_dict[role]:
							roles_list[index]['features'].append(entry)
							print("\t\t  new feature:\t" + entry)

				####################################
				# New Localization
				loc_dict = dict()
				for entry in loc.split(';'):
					if(':' in entry):
						print(entry)
						(cpt,gene,sources)=entry.split(':')
						loc_dict[gene]=sources.split('|')
					# Assumed reaction compartment
					else:
						cpt=entry
						loc_dict[gene]=[]

					if(cpt not in roles_list[index]['localization']):
						print('\t\t  new cpt:\t' + entry)
						roles_list[index]['localization'][cpt] = dict()
					elif(gene not in roles_list[index]['localization'][cpt]):
						print('\t\t  new gene:\t' + entry)
						roles_list[index]['localization'][cpt][gene]=loc_dict[gene]
					else:
						for src in loc_dict[gene]:
							if(src not in roles_list[index]['localization'][cpt][gene]):
								print('\t\t  new source:\t' + entry)
								roles_list[index]['localization'][cpt][gene].append(src)

				####################################
				# New Publication
				if(not set(pub).issubset(set(pubs_dict[role]))):
					for entry in pub:
						if entry not in pubs_dict[role]:
							roles_list[index]['publications'].append(entry)
							print("\t\t  new publication:\t" + entry)
				
				if(cur != ''):
					for curator in cur.split(';'):
						if('curators' not in roles_list[index]):
							roles_list[index]['curators']=list()
						if(curator not in roles_list[index]['curators']):
							roles_list[index]['curators'].append(curator)

			####################################
			# ADD NEW ROLE
			else:
				print("New Role\t" + role)
				new_role = {'role':'',
							'include':True,
							'subsystems':[],
							'classes':{},
							'features':[],
							'reactions':[],
							'localization':{},
							'publications':[],
							'predictions':{},
							'sequences':{},
							'type':'universal'}

				####################################
				# Add function
				new_role['role']=role

				####################################
				# Add subsystem and class
				class_dict=dict()
				for entry in ss.split('||'):
					new_role['subsystems'].append(entry)
					class_dict[entry]=[]

					# Add pathway
					if(pwys != ""):
						for pwy in pwys.split('||'):
							class_dict[entry].append(pwy)

				new_role['classes'][cls]=class_dict

				####################################
				# Add reaction
				for entry in rxn.split(';'):
					new_role['reactions'].append(entry)
					if(entry not in new_complex_rxns_dict):
						new_complex_rxns_dict[entry]=list()
					if(role not in new_complex_rxns_dict[entry]):
						new_complex_rxns_dict[entry].append(role)

				####################################
				# Add genes
				if(ftr != ""):
					for entry in ftr.split(';'):
						new_role['features'].append(entry)

				####################################
				# Add publications
				if(pub != ""):
					for entry in pub.split(','):
						new_role['publications'].append(entry)

				####################################
				# Add localization
				for entry in loc.split(';'):
					loc_dict=dict()
					#if protein localization data used
					if(':' in entry):
						(cpt,gene,sources)=entry.split(':')
						loc_dict[gene]=sources.split('|')
					#assumed reaction compartment
					else:
						cpt=entry
						loc_dict[rxn]=[]

					if(cpt not in new_role['localization']):
						new_role['localization'][cpt] = dict()
					new_role['localization'][cpt][gene]=loc_dict[gene]

				####################################
				# Add cofactors
				if(cof != ''):
					if('cofactors' not in new_role):
						new_role['cofactors']=list()
					new_role['cofactors'].append(cof)

				####################################
				# Homomers
				if(hom != '' and int(hom)>1):
					new_role['homomers']=int(hom)

				####################################
				# Activate?
				if(inc != ''):
					if(inc == 'include'):
						new_role['include']=True
					if(inc == 'exclude'):
						new_role['include']=False

				####################################
				# type
				if(typ != ''):
					new_role['type']=typ

				####################################
				# curators
				if(cur != ''):
					new_role["curators"] = list()
					for curator in cur.split(';'):
						new_role['curators'].append(curator)

				####################################
				# Add predictions
				for ftr in new_role['features']:
					# print(ftr)
					if(ftr in predicted_genes_dict):
						# print(ftr)
					# you need to add the predicted genes and their PSI to
					# the new_role['predictions'] dict
					# there's a hint on how to do it in the 'Add sequences' below
					# But you need to add "Uniprot||" to the ftr to make a match
						new_role['predictions'][ftr]=predicted_genes_dict[ftr]
						#pass

				####################################
				# Add sequences
				for ftr in new_role['features']:
					# print(ftr)
					if(ftr in updated_protein_sequences_dict):
						print("match")
						# print(ftr)
						# NB: in it's current state, this won't happen
						# can you figure out why?
						new_role['sequences'][ftr]= updated_protein_sequences_dict[ftr] #protseq_dict[ftr]

				####################################
				# Update dictionaries and roles list
				roles_dict[role] = line
				rxns_dict[role] = rxn
				ftrs_dict[role] = ftr
				roles_list.append(new_role)

with open(db_file,'w') as new_subsystem_file:
	json.dump(roles_list,new_subsystem_file,indent=4)
# print(json.dumps(roles_list,indent=4))

## Update complexes
with open("../../../Data/PlantSEED_v3/Complex/Consolidated_PlantSEED_Complex_Curation.json") as complex_file:
	reactions_list = json.load(complex_file)

print(json.dumps(new_complex_rxns_dict,indent=2))
for curated_rxn in reactions_list:
	rxn=curated_rxn.split('_')[0]
	if(rxn not in new_complex_rxns_dict):
		continue

	print(rxn)

	for role in reactions_list[curated_rxn]['roles']:
		if(role['role'] not in new_complex_rxns_dict[rxn]):
			print(rxn,role['role'],json.dumps(role,indent=2))
#		if(role['role'] in updated_roles_dict):
#			lst = updated_roles_dict[role['role']]
#			role['role'] = lst[2]

#with open("../../../../Data/PlantSEED_v3/Complex/Consolidated_PlantSEED_Complex_Curation.json",'w') as new_complex_file:
#	json.dump(reactions_list,new_complex_file,indent=4)
		