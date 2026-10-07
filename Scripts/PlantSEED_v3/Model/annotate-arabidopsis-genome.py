import argparse
import json
import re,os
from copy import deepcopy
from urllib.request import urlopen

PS_url = 'https://raw.githubusercontent.com/ModelSEED/PlantSEED/'
PS_tag = 'dev'

# Scripts/PlantSEED_v3/Model/ -> repo root is three levels up.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
LOCAL_ROLES_FILE = os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Roles.json")

# These should be retrieved from the Template data
template_compartment_mapping={'c':'cytosol', 'g':'golgi', 'w':'cellwall',
							  'n':'nucleus', 'r':'endoplasm',
							  'v':'vacuole', 'cv':'vacuole',
							  'd':'plastid', 'cd':'plastid',
							  'm':'mitochondria','cm':'mitochondria',
							  'mj':'mitointer', 'ce':'extracellular',
							  'x':'peroxisome', 'cx':'peroxisome',
							  'e':'extracellular','de':'plastid','dy':'thylakoid'}

class FetchPlantSEEDImpl:

	def fetch_reactions(self, PS_Roles):

		reactions_data = dict()

		for entry in PS_Roles:
			if(entry['include'] is False):
				# print(entry['role'])
				continue

			main_class_ss = list()
			main_class = list()
			for metabolic_class in entry['classes']:
				if(len(entry['classes'][metabolic_class].keys())>0):
					main_class.append(metabolic_class)

				for ss in entry['classes'][metabolic_class].keys():
					if(ss not in main_class_ss):
						main_class_ss.append(ss)

			for rxn in entry['reactions']:
				if(rxn not in reactions_data):
					reactions_data[rxn]={'ecs':[],
										 'roles':[],
										 'classes':[],
										 'subsystems':[],
										 'compartments':[]}

				if(entry['role'] not in reactions_data[rxn]['roles']):
					reactions_data[rxn]['roles'].append(entry['role'])

				for mclass in main_class:
					if(mclass not in reactions_data[rxn]['classes']):
						reactions_data[rxn]['classes'].append(mclass)

				for subsystem in main_class_ss:
					if(subsystem not in reactions_data[rxn]['subsystems']):
						reactions_data[rxn]['subsystems'].append(subsystem)

				for cpt in entry['localization']:
					if(cpt not in reactions_data[rxn]['compartments']):
						reactions_data[rxn]['compartments'].append(cpt)

		for rxn in reactions_data:
			for role in reactions_data[rxn]['roles']:
				if('EC' in role):
					match = re.search(r"\d+\.[\d-]+\.[\d-]+\.[\d-]+", role)
					if(match is not None):
						if(match.group(0) not in reactions_data[rxn]['ecs']):
							reactions_data[rxn]['ecs'].append(match.group(0))

		print("Collected "+str(len(reactions_data))+" core reactions")
		return reactions_data

	def fetch_features(self, PS_Roles):

		features_data = dict()

		for entry in PS_Roles:
			if(entry['include'] is False):
			    continue

			for feature in entry['features']:
				if(feature not in features_data):
					features_data[feature]= {'roles':[],
											 'compartments':[]}

				if(entry['role'] not in features_data[feature]['roles']):
					features_data[feature]['roles'].append(entry['role'])

				if('localization' not in entry):
					continue
                                
				for compartment in entry['localization']:
					for curated_ftr in entry['localization'][compartment]:
						if(curated_ftr == feature):
							if(compartment not in features_data[feature]['compartments']):
								features_data[feature]['compartments'].append(compartment)

		# consolidate and create functions
		# this is the heart of all PlantSEED annotation
		for feature in features_data:

			# compose function as sorted roles
			feature_function = " / ".join( sorted( features_data[feature]['roles'] ) )

			# collect mapped compartments
			feature_compartment_list =  list()
			for compartment in sorted( features_data[feature]['compartments'] ):
				if(compartment not in template_compartment_mapping):
					print("WARNING, missing compartment: ",compartment)
				mapped_compartment = template_compartment_mapping[compartment]
				feature_compartment_list.append(mapped_compartment)

			# compose sorted list of compartments
			# NB: these are sorted according to single-letter identifier
			feature_compartments = ""
			if(len(feature_compartment_list)>0):
				feature_compartments = " # "+" # ".join( feature_compartment_list )

			full_function = feature_function+feature_compartments
			features_data[feature]['function']=full_function

		return(features_data)
	
	def fetch_roles(self, roles_file=None):
		"""Load PlantSEED_Roles.json from an explicit local path, else fall
		back to fetching it over HTTP from the PS_tag branch on GitHub."""
		if roles_file:
			print(f"Loading roles from local file: {roles_file}")
			with open(roles_file) as fh:
				return json.load(fh)

		print(f"Loading roles from https://github.com/ModelSEED/PlantSEED ({PS_tag} branch)")
		return json.load(urlopen(PS_url+PS_tag+'/Data/PlantSEED_v3/PlantSEED_Roles.json'))

	def __init__(self):
		pass

def _resolve_roles_source(args):
	"""Decide which PlantSEED_Roles.json to load, honouring --local/--remote
	if given, otherwise detecting a local checkout and asking the curator."""
	if args.remote:
		return None
	if args.local:
		if not os.path.isfile(LOCAL_ROLES_FILE):
			raise SystemExit(f"--local given but no file found at {LOCAL_ROLES_FILE}")
		return LOCAL_ROLES_FILE

	if not os.path.isfile(LOCAL_ROLES_FILE):
		return None  # no local checkout to offer -- fetch from GitHub

	if args.quiet:
		return LOCAL_ROLES_FILE  # non-interactive: local checkout wins by default

	print(f"Found a local PlantSEED_Roles.json at:\n  {LOCAL_ROLES_FILE}")
	choice = input(
		f"Use this local file (uncommitted edits included), or fetch from "
		f"GitHub's '{PS_tag}' branch instead? [local/remote] (local): "
	).strip().lower()
	if choice in ("", "l", "local"):
		return LOCAL_ROLES_FILE
	return None


def _build_argparser():
	ap = argparse.ArgumentParser(
		description="Build an annotated Arabidopsis genome JSON from "
		            "PlantSEED_Roles.json, for feeding into the reconstruction pipeline.",
	)
	ap.add_argument("--local", action="store_true",
		help=f"Force loading the local checkout's PlantSEED_Roles.json "
		     f"(default: {LOCAL_ROLES_FILE}), including uncommitted curation. "
		     f"Skips the local/remote prompt.")
	ap.add_argument("--remote", action="store_true",
		help=f"Force fetching PlantSEED_Roles.json from GitHub's "
		     f"'{PS_tag}' branch, even if a local checkout is present. "
		     f"Skips the local/remote prompt.")
	ap.add_argument("--quiet", action="store_true",
		help="Don't prompt when both a local file and the default behaviour "
		     "could apply -- just use the local checkout if one exists.")
	return ap


def main():

	print("Warning: refactor template compartments")

	args = _build_argparser().parse_args()
	if args.local and args.remote:
		raise SystemExit("--local and --remote are mutually exclusive")
	roles_file = _resolve_roles_source(args)

	plantseed = FetchPlantSEEDImpl()
	# Load these directly from PlantSEED_Roles.json
	PS_Roles = plantseed.fetch_roles(roles_file=roles_file)
	plantseed_features = plantseed.fetch_features(PS_Roles)

	genome_obj = dict()
	with open('empty-genome.json') as fh:
		genome_obj=json.load(fh)

	arabidopsis_genome = deepcopy(genome_obj)
	for spp_ftr in plantseed_features:
		spp,ftr = spp_ftr.split('||')
		if(spp != "Athaliana_TAIR10"):
			continue

		feature = {'id':ftr,'functions':[plantseed_features[spp_ftr]['function']]}
		arabidopsis_genome['features'].append(feature)

	with open('annotated-arabidopsis-genome.json','w') as fh:
		fh.write(json.dumps(arabidopsis_genome,indent=2))

if(__name__ == "__main__"):
	main()
