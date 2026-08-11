import copy
import json
import os,re
import sys

class ReconstructAppImpl:
	#: Suppress progress output entirely. Progress goes to stderr either way —
	#: stdout is reserved for machine-readable output, because every delivery
	#: surface parses it: koros ingests `plantseed capabilities --json`, the
	#: modelseed-api job scripts read a JSON job record, and a CTS container's
	#: stdout is captured as a log artifact. A stray print() on stdout corrupts
	#: all three, and does so silently.
	quiet = False

	#: Where progress goes. Swappable so a caller can capture it — a KBase app
	#: routing progress into a KBaseReport, or a test asserting on it — without
	#: touching this class.
	log_stream = None

	def _log(self, *args):
		if self.quiet:
			return
		print(*args, file=self.log_stream or sys.stderr)

	@staticmethod
	def _convert_search_role(role):

		searchrole = role

		#Remove spaces
		searchrole = searchrole.strip()
		searchrole = searchrole.replace(' ','')

		#Make all lowercase
		searchrole = searchrole.lower()

		#Remove EC and parentheses
		searchrole = re.sub(r'\(ec[\d-]+\.[\d-]\.[\d-]\.[\d-]\)', '', searchrole)

		return searchrole

	def _set_objects(self,params):

		self.genome_obj=params['genome']
		self.template_obj=params['template']

	def reconstruct_metabolism(self,input_params,log_rxn=None):

		searchroles_dict = dict()
		roles_dict = dict()
		for role in self.template_obj['roles']:
			searchrole = self._convert_search_role(role['name'])
			searchroles_dict[searchrole]=role['id']
			roles_dict[role['id']]=role

		complex_dict = dict()
		for cpx in self.template_obj['complexes']:
			complex_dict[cpx['id']]=cpx

		abbrev_cpt_dict=dict()
		for cpt in input_params['cpts']:
			abbrev_cpt_dict[input_params['cpts'][cpt]['abbrev']]=cpt

		#Retrieve Genome annotation as dict
		role_cpt_ftr_dict=dict()
		# genome_ref = input_params['input_ws']+'/'+input_params['input_genome']
		# genome_obj = self.dfu.get_objects({'object_refs': [genome_ref]})['data'][0]['data']
		for feature in self.genome_obj['features']:
			if('functions' in feature and len(feature['functions'])>0):
				for function_comment in feature['functions']:

					# print(function_comment)
					#Split for comments and retrieve compartments
					function_cpt_list = function_comment.split("#")
					for i in range(len(function_cpt_list)):
						function_cpt_list[i]=function_cpt_list[i].strip()

					function = function_cpt_list.pop(0)
					# This regex is very old. As I have control over the annotation
					# of plant genomes, I only use the forward slash to separate roles
					# roles = re.split("\s*;\s+|\s+[\@\/]\s+", function)
					roles = re.split("\\s+/\\s+",function)
					for role in roles:
						
						searchrole = self._convert_search_role(role)

						if(searchrole not in searchroles_dict):
							if(searchrole != 'unannotated'):
								# These are roles that are in PlantSEED but not yet 
								# included in the template
								pass
							continue
							
						role_id = searchroles_dict[searchrole]

						if(role_id not in role_cpt_ftr_dict):
							role_cpt_ftr_dict[role_id]=dict()

						# Defaults to cytosol
						if(len(function_cpt_list)==0):
							function_cpt_list.append('cytosol')

						for cpt in function_cpt_list:
							abbrev_cpt=cpt
							if(cpt not in abbrev_cpt_dict):
								self._log("No compartmental abbreviation found for "+cpt)
							else:
								abbrev_cpt = abbrev_cpt_dict[cpt]

							if(abbrev_cpt not in role_cpt_ftr_dict[role_id]):
								role_cpt_ftr_dict[role_id][abbrev_cpt]=dict()

							role_cpt_ftr_dict[role_id][abbrev_cpt][feature['id']]=1
					
		# Default dictionaries for objects needed for a model reaction
		default_mdlcpt_dict = { 'id': 'u0', 'label': 'unknown',
								'pH': 7, 'potential': 0, 'compartmentIndex': 0,
								'compartment_ref': '~//' }

		default_mdlcpd_dict = { 'id': '', 'charge': 0, 'formula': '',
								'name': '', 'compound_ref': '',
								'modelcompartment_ref': '~/modelcompartments/id/u0' }

		default_mdlrxn_dict = { 'id': '', 'direction': '', 'protons': 0,
								'name': '', 'reaction_ref': '', 'probability': 0,
								'modelcompartment_ref': '',
								'modelReactionReagents': [], 'modelReactionProteins': [] }

		# Lookup dictionaries for compartments and compounds, to avoid duplicating them
		mdlcpts_dict = dict()
		mdlcpds_dict = dict()
		
		# Reaction complexes for the generated table
		rxncplxs_dict = dict()

		# 'template_ref' : template_ref, 'genome_ref' : genome_ref, 
		# Create New, but Empty Plant Reconstruction
		new_model_obj = { 'id' : input_params['id'], 'name' : input_params['name'],
				   			'template_ref':'','genome_ref':'',
				   			'type' : "GenomeScale", 'source' : "KBase", 'source_id' : "PlantSEED_v3", 
							'modelreactions' : [], 'modelcompounds' : [], 'modelcompartments' : [], 'biomasses' : [],
							'gapgens' : [], 'gapfillings' : [] }
		
		# collect compound names
		cpd_nms = dict()
		for template_cpd in self.template_obj['compounds']:
			cpd_nms[template_cpd['id']]=template_cpd['name']

		conditional_spontaneous_reactions = list()
		for template_rxn in self.template_obj['reactions']:
			if(template_rxn['type'] == 'gapfilling'):
				continue

			if(log_rxn is not None and log_rxn in template_rxn['id']):
				self._log(template_rxn)

			template_rxn_cpt = template_rxn['templatecompartment_ref'].split('/')[-1]

			proteins_list = list()
			prots_str_list = list()

			# complex_ref and source are optional fields
			default_protein_dict = {'note':template_rxn['type'], 'complex_ref':'', 'modelReactionProteinSubunits':[]}
			for cpx_ref in template_rxn['templatecomplex_refs']:
				cpx_id = cpx_ref.split('/')[-1]
				model_complex_ref = "~/template/complexes/id/"+cpx_id

				new_protein_dict = copy.deepcopy(default_protein_dict)
				new_protein_dict['complex_ref']=model_complex_ref

				complex_present=False
				subunits_list = list()
				default_subunit_dict = {'role':'','triggering':0,'optionalSubunit':0,'note':'','feature_refs':[]}
				matched_role_dict = dict()

				for cpxrole in complex_dict[cpx_id]['complexroles']:
					role_id = cpxrole['templaterole_ref'].split('/')[-1]
					# print("Testing "+roles_dict[role_id]['name']+" for reaction "+template_rxn['id'])
					if(role_id in role_cpt_ftr_dict):
						for role_cpt in role_cpt_ftr_dict[role_id]:
					
							role_cpt_present=False
							if(template_rxn_cpt == role_cpt and cpxrole['triggering'] == 1):
								complex_present=True
								role_cpt_present=True

							if(role_cpt_present == True):
								new_subunit_dict = copy.deepcopy(default_subunit_dict)
								new_subunit_dict['triggering'] = cpxrole['triggering']
								new_subunit_dict['optionalSubunit'] = cpxrole['optional_role']
								new_subunit_dict['role'] = roles_dict[role_id]['name']

								if(len(roles_dict[role_id]['features'])>0):
									new_subunit_dict['note'] = 'Features characterized and annotated'
								else:
									#This never happens as of Fall 2019
									self._log("Warning: "+roles_dict[role_id]['name']+" is apparently uncharacterized!")
									new_subunit_dict['note'] = 'Features uncharacterized but annotated'
									pass

								for ftr in role_cpt_ftr_dict[role_id][role_cpt]:
									feature_ref = "~/genome/features/id/"+ftr
									new_subunit_dict['feature_refs'].append(feature_ref)
								
								matched_role_dict[role_id]=1
								subunits_list.append(new_subunit_dict)

					if(role_id not in role_cpt_ftr_dict and template_rxn['type'] == 'universal'):
						# This should still be added, with zero features to indicate the universality of the role in plant primary metabolism
						# This will include universal "Spontaneous Reaction"s

						new_subunit_dict = copy.deepcopy(default_subunit_dict)
						new_subunit_dict['triggering'] = cpxrole['triggering']
						new_subunit_dict['optionalSubunit'] = cpxrole['optional_role']
						new_subunit_dict['role'] = roles_dict[role_id]['name']

						# print("Role "+roles_dict[role_id]['name']+" not in genome but reaction "+template_rxn['id']+" is universal")

						# Un-necessary, but explicitly stated
						new_subunit_dict['feature_refs']=[]

						if(len(roles_dict[role_id]['features'])==0):
							new_subunit_dict['note'] = 'Features uncharacterized and unannotated'
						else:
							new_subunit_dict['note'] = "Features characterized but unannotated"
							
							# This includes UniProt annotation and annotation from other genomes
							if(len(roles_dict[role_id]['features']) > 0 and 'Athaliana' in roles_dict[role_id]['features'][0]):
								# print("Missing annotation: ",cpx_id,role_id,roles_dict[role_id]['name'],roles_dict[role_id]['features'])
								pass

						matched_role_dict[role_id]=1
						subunits_list.append(new_subunit_dict)
						
				if(complex_present == True):
					# Check to see if members of a detected protein complex are missing
					# and add them if so, to round off the complex
					# This will only happen to a complex that is conditional (see above)
					for cpxrole in complex_dict[cpx_id]['complexroles']:
						role_id = cpxrole['templaterole_ref'].split('/')[-1]
						
						if(role_id not in matched_role_dict):
							# print("Gapfilling complex: ",cpx_id,roles_dict[role_id])
							new_subunit_dict = copy.deepcopy(default_subunit_dict)
							new_subunit_dict['role'] = role_id
							new_subunit_dict['triggering'] = cpxrole['triggering']
							new_subunit_dict['optionalSubunit'] = cpxrole['optional_role']
							new_subunit_dict['note'] = "Complex-based-gapfilling"
							subunits_list.append(new_subunit_dict)

				if(len(subunits_list)>0):
					new_protein_dict['modelReactionProteinSubunits']=subunits_list

					# Store features and subunits as complex string for table
					subs_str_list=list()
					for subunit in subunits_list:
						ftrs_str_list=list()
						for ftr_ref in subunit['feature_refs']:
							ftr = ftr_ref.split('/')[-1]
							ftrs_str_list.append(ftr)
						ftr_str = "("+", ".join(ftrs_str_list)+")"
						subs_str_list.append(ftr_str)
					sub_str = "["+", ".join(subs_str_list)+"]"
					prots_str_list.append(sub_str)

				proteins_list.append(new_protein_dict)

			prot_str = ", ".join(prots_str_list)

			# This is important, we need to use role-based annotation to determine whether
			# a reaction should even be added to the model
			is_conditional_spontaneous = False
			if(template_rxn['type'] == 'conditional'):

				# We add the reaction to the model if we find that there are features associated with it
				has_features = False
				for protein in proteins_list:
					for subunit in protein['modelReactionProteinSubunits']:
						if(len(subunit['feature_refs'])>0):
							has_features = True

				# However, if there are no features, but it is a Spontaneous Reaction, we want to flag it
				# We will add it to the model if it contains metabolites found in the model
				# We can't really check that comprehensively until we've built the rest of the model
				# So we collect them here before ignoring other conditional reactions
				if(has_features is False):

					skipping_roles = list()
					skipping_features = list()
					for cpx_ref in template_rxn['templatecomplex_refs']:
						for cpxrole in complex_dict[cpx_id]['complexroles']:
							role_id = cpxrole['templaterole_ref'].split('/')[-1]

							if('spontaneous reaction' in roles_dict[role_id]['name'].lower()):
								is_conditional_spontaneous = True

							if(roles_dict[role_id]['name'] not in skipping_roles):
								skipping_roles.append(roles_dict[role_id]['name'])
							for ftr in roles_dict[role_id]['features']:
								if(ftr not in skipping_features):
									skipping_features.append(ftr)

					if(log_rxn is not None and log_rxn in template_rxn['id']):
						self._log(proteins_list)

					if(is_conditional_spontaneous is False):
						self._log("Skipping conditional reaction because curated features are not in genome",template_rxn['id'],skipping_roles,skipping_features)
						continue

			if(log_rxn is not None and log_rxn in template_rxn['id']):
				self._log("Adding")
				self._log(template_rxn['type'],proteins_list)

			# If the check passes, then, here, we instantiate the actual reaction that goes into the model
			new_mdlrxn_id = template_rxn['id']+'0'
			new_mdlcpt_id = template_rxn_cpt+'0'
			base_rxn_id = template_rxn['id'].split('_')[0]

			# For table
			rxncplxs_dict[new_mdlrxn_id]=prot_str

			new_mdlrxn_dict = copy.deepcopy(default_mdlrxn_dict)
			new_mdlrxn_dict['id'] = new_mdlrxn_id

			# new_mdlrxn_dict['name'] = MSD_reactions_dict[base_rxn_id]['abbreviation']
			# if(MSD_reactions_dict[base_rxn_id]['abbreviation'] == ""):
			new_mdlrxn_dict['name']=base_rxn_id

			new_mdlrxn_dict['direction'] = template_rxn['direction']
			new_mdlrxn_dict['reaction_ref']='~/template/reactions/id/'+template_rxn['id']
			new_mdlrxn_dict['modelcompartment_ref']='~/modelcompartments/id/'+new_mdlcpt_id

			#Here we check and instantiate a new modelcompartment
			if(new_mdlcpt_id not in mdlcpts_dict):
				new_mdlcpt_dict = copy.deepcopy(default_mdlcpt_dict)
				new_mdlcpt_dict['id']=new_mdlcpt_id
				new_mdlcpt_dict['label']=input_params['cpts'][template_rxn_cpt]['name']
				new_mdlcpt_dict['compartment_ref']='~/template/compartments/id/'+template_rxn_cpt
				mdlcpts_dict[new_mdlcpt_id]=new_mdlcpt_dict

			#Add Proteins as previously determined
			new_mdlrxn_dict['modelReactionProteins']=proteins_list

			#Add Reagents
			for template_rgt in template_rxn['templateReactionReagents']:
				template_rgt_cpd_cpt_id = template_rgt['templatecompcompound_ref'].split('/')[-1]
				(template_rgt_cpd,template_rgt_cpt)=template_rgt_cpd_cpt_id.split('_')

				#Check and add new model compartment 
				new_mdlcpt_id = template_rgt_cpt+'0'
				if(new_mdlcpt_id not in mdlcpts_dict):
					new_mdlcpt_dict = copy.deepcopy(default_mdlcpt_dict)
					new_mdlcpt_dict['id']=new_mdlcpt_id
					new_mdlcpt_dict['label']=input_params['cpts'][template_rxn_cpt]['name']
					new_mdlcpt_dict['compartment_ref']='~/template/compartments/id/'+template_rgt_cpt
					mdlcpts_dict[new_mdlcpt_id]=new_mdlcpt_dict
			   
				#Add new model compounds
				new_mdlcpd_id = template_rgt_cpd_cpt_id+'0'
				base_cpd_id = template_rgt_cpd_cpt_id.split('_')[0]

				if(new_mdlcpd_id not in mdlcpds_dict):
					new_mdlcpd_dict = copy.deepcopy(default_mdlcpd_dict)
					new_mdlcpd_dict['id']=new_mdlcpd_id
					new_mdlcpd_dict['name']=cpd_nms[new_mdlcpd_id.split('_')[0]]
					new_mdlcpd_dict['compound_ref']='~/template/compounds/id/'+template_rgt_cpd
					new_mdlcpd_dict['modelcompartment_ref']='~/modelcompartments/id/'+new_mdlcpt_id
					mdlcpds_dict[new_mdlcpd_id]=new_mdlcpd_dict

				new_rgt_dict = {'coefficient' : template_rgt['coefficient'],
								'modelcompound_ref' : '~/modelcompounds/id/'+new_mdlcpd_id}

				new_mdlrxn_dict['modelReactionReagents'].append(new_rgt_dict)

			if(log_rxn is not None and log_rxn in template_rxn['id']):
				self._log(new_mdlrxn_dict)

			if(is_conditional_spontaneous is False):
				new_model_obj['modelreactions'].append(new_mdlrxn_dict)
			else:
				conditional_spontaneous_reactions.append(new_mdlrxn_dict)

		#Having populated with list of reactions and biomass (to come), then add all compartments and compounds
		for cpt_id in mdlcpts_dict:
			new_model_obj['modelcompartments'].append(mdlcpts_dict[cpt_id])

		#Last, but key modelcompound is the biomass, need to add it explicitly
		biocpd_id = "cpd11416"
		mdlbiocpd_dict = copy.deepcopy(default_mdlcpd_dict)
		mdlbiocpd_dict['id'] = biocpd_id+'_c0'
		mdlbiocpd_dict['name'] = 'Biomass'
		mdlbiocpd_dict['compound_ref'] = "~/template/compounds/id/"+biocpd_id
		mdlbiocpd_dict['modelcompartment_ref'] = "~/modelcompartments/id/c0"
		mdlcpds_dict[mdlbiocpd_dict['id']] = mdlbiocpd_dict

		for cpd_id in mdlcpds_dict:
			new_model_obj['modelcompounds'].append(mdlcpds_dict[cpd_id])

		default_biomass_dict = { 'id': 'bio1', 'name': 'Plant leaf biomass', 'other': 1,
								 'dna': 0, 'rna': 0, 'protein': 0, 'cellwall': 0,
								 'lipid': 0, 'cofactor': 0, 'energy': 0, 'biomasscompounds': [] }

		default_biocpd_dict = { 'modelcompound_ref' : '', 'coefficient' : 0 }

		for template_biomass in self.template_obj['biomasses']:
			new_template_biomass = copy.deepcopy(default_biomass_dict)
			new_template_biomass['id'] = template_biomass['id']
			new_template_biomass['name'] = template_biomass['name']

			for entry in ['dna','rna','protein','cellwall','lipid','cofactor','energy','specialized','other']:
				new_template_biomass[entry] = template_biomass[entry]

			for template_cpd in template_biomass['templateBiomassComponents']:
				new_biocpd_dict = copy.deepcopy(default_biocpd_dict)
				mdlcpd_id = template_cpd['templatecompcompound_ref'].split('/')[-1]+'0'
				if(mdlcpd_id not in mdlcpds_dict):
					self._log("Template biomass cpd not found in model:",template_cpd)
					continue
				new_biocpd_dict['modelcompound_ref'] = '~/modelcompounds/id/'+mdlcpd_id
				new_biocpd_dict['coefficient'] = template_cpd['coefficient']
				new_template_biomass['biomasscompounds'].append(new_biocpd_dict)
		
			new_model_obj['biomasses'].append(new_template_biomass)

		# Finally, we go through the list of conditional spontaneous reactions
		# We add them to the model if all the metabolites are involved in the model
		if(len(conditional_spontaneous_reactions)>0):

			for mdlrxn in conditional_spontaneous_reactions:

				mdlcpd_in_model = False
				for mdlcpd in mdlrxn['modelReactionReagents']:
					mdlcpd_id = mdlcpd['modelcompound_ref'].split('/')[-1]

					if(mdlcpd_id in mdlcpds_dict):
						mdlcpd_in_model = True

				if(mdlcpd_in_model is True):

					# We have to iterate and make sure that any compounds in the reaction but not in the model
					for mdlcpd in mdlrxn['modelReactionReagents']:
						mdlcpd_id = mdlcpd['modelcompound_ref'].split('/')[-1]
						if(mdlcpd_id not in mdlcpds_dict):
							self._log("Missing mdlcpd: ",mdlcpd_id)
							pass

					self._log("Adding conditional spontaneous reaction",mdlrxn['id'])
					new_model_obj['modelreactions'].append(mdlrxn)

		return new_model_obj

def main():

	genome_path = 'Ptrichocarpa_533_v4.1.protein-annotated.json'
	genome_path = 'Sbicolor_454_v3.1.1.protein-annotated.json'
	genome_path = 'Sbicolor_730_v5.1.protein-annotated.json'
	genome_path = 'annotated-arabidopsis-genome.json'

	with open(genome_path) as fh:
		genome_obj = json.load(fh)

	template_file_path = os.path.join('..','Template','PlantSEED_Biomass_Template.json')
	with open(template_file_path) as fh:
		template_obj = json.load(fh)

	# Compile compartment information
	compartments_file_path = os.path.join('..','..','..','Data','PlantSEED_v3','Compartments','PlantSEED_Compartments.json')
	with open(compartments_file_path) as fh:
		compartments = json.load(fh)

	reconstruct_app = ReconstructAppImpl()
	reconstruct_app._set_objects({'genome':genome_obj,'template':template_obj})

	obj_name = 'test_model'
	input_params={'id':obj_name,'name':obj_name,'cpts':compartments}
	metabolism_obj = reconstruct_app.reconstruct_metabolism(input_params,log_rxn=None)
	
	# When loading a metabolic model into KBase, it complains if certain attributes
	# for compounds are not populated, but these should be propagated from the
	# template so I'm not sure whey they're not being populated

	# biochem_path = os.path.join(test_data_root,"MS_Cpds_Attrs.json")
	# biochem_fh = open(biochem_path)
	# biochem_obj = json.load(biochem_fh)
		
	for mdlcpd in metabolism_obj['modelcompounds']:
		base_cpd_id = mdlcpd['id'].split('_')[0]

		# if(base_cpd_id not in biochem_obj):
		#	continue

		# mdlcpd['name'] = biochem_obj[base_cpd_id]['name']
		# mdlcpd['charge'] = float(biochem_obj[base_cpd_id]['charge'])
		# mdlcpd['formula'] = biochem_obj[base_cpd_id]['formula']

		# if(mdlcpd['formula'] is None):
		# 	mdlcpd['formula'] = ""

		# if(' ' in mdlcpd['formula']):
		# 	print(mdlcpd['id'],mdlcpd['formula'])
			
	output_path=os.path.join(obj_name+'.json')
	with open(output_path,'w') as mofh:
		mofh.write(json.dumps(metabolism_obj, indent=4, sort_keys=True))

if(__name__ == "__main__"):
	main()
