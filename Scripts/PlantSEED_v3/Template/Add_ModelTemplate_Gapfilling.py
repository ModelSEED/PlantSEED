#!/usr/bin/env python
from urllib.request import urlopen
import sys
import json
import string

#bioObj_ref = "/chenry/public/modelsupport/biochemistry/plantdefault.biochem" #PMS reference
biochem_ref = "48/8/1" #AppDev reference

############################
## Load Template
############################

with open("PlantSEED_Biomass_Template.json") as template_file:
    plantseed_template_obj = json.load(template_file)

check_tpl_cpt_dict = dict()
for template_compartment in plantseed_template_obj['compartments']:
    check_tpl_cpt_dict[template_compartment['id']]=1

check_tpl_cpd_dict = dict()
for template_compound in plantseed_template_obj['compounds']:
    check_tpl_cpd_dict[template_compound['id']]=1

check_tpl_cpcpd_dict = dict()
for template_compcompound in plantseed_template_obj['compcompounds']:
    check_tpl_cpcpd_dict[template_compcompound['id']]=1

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
# The asymmetric transport is now encoded in the PlantSEED roles file.
# I'm leaving this note as it's an important distinction that may be lost.

############################
## Load Biochemistry
############################

MSD_git_url = "https://raw.githubusercontent.com/ModelSEED/ModelSEEDDatabase/"
MSD_commit = "v1.1.1"

biochemistry_reactions = json.load(urlopen(MSD_git_url+MSD_commit+"/Biochemistry/reactions.json"))
reactions_dict=dict()
for reaction in biochemistry_reactions:
    reactions_dict[reaction['id']]=reaction

biochemistry_compounds = json.load(urlopen(MSD_git_url+MSD_commit+"/Biochemistry/compounds.json"))
compounds_dict=dict()
for compound in biochemistry_compounds:

    # fix default values
    for key in ["charge","mass","deltag","deltagerr"]:
        if(compound[key] is None):
            compound[key] = 0.0

    if(compound['formula'] is None):
        compound['formula'] = 'R'

    template_compound_hash = { 'id':compound['id'], 'name':compound["name"],
                               'abbreviation':compound["abbreviation"], 'aliases':[],
                               'formula':compound["formula"], 'isCofactor':0,
                               'defaultCharge':float(compound["charge"]), 'mass':float(compound["mass"]),
                               'deltaG':float(compound["deltag"]), 'deltaGErr':float(compound["deltagerr"]),
                               'compound_ref':biochem_ref+"/compounds/id/"+compound['id'] }

    compounds_dict[compound['id']]=template_compound_hash

#Collect compartments
remote_file = urlopen(MSD_git_url+MSD_commit+"/Templates/Plant/Compartments.tsv")
compartments = dict()
header=1
for line in remote_file.readlines():
    line=line.decode('utf-8')
    line=line.rstrip('\r\n')
    columns_list=line.split('\t')

    #skip header
    if(header):
        header=0
        continue

    cpt_hash = {'id' : columns_list[1], 'name' : columns_list[2],
                'hierarchy' : int(columns_list[3]), 'pH' : int(columns_list[4]),
                'aliases' : columns_list[5].split(',')}
    compartments[columns_list[1]]=cpt_hash

############################
## Load PlantSEED
############################

#Load Core Subsystems
#Load PlantSEED Subsystems, Roles, Reactions
with open("../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

#Collect Compartmentalized Reactions
reactions_roles=dict()
for entry in roles_list:
#    if(entry['include'] is False):
#        continue
        
    for rxn in entry['reactions']:
        for cpt in entry['localization']:
            tmpl_rxn = rxn+"_"+cpt
            if(tmpl_rxn not in reactions_roles):
                reactions_roles[tmpl_rxn]=list()
            if(entry['role'] not in reactions_roles[tmpl_rxn]):
                reactions_roles[tmpl_rxn].append(entry['role'])

############################
## Begin Gapfilling Reaction Generation
############################

for template_reaction in reactions_roles:

    [base_reaction,reaction_cpts]=template_reaction.split('_')

    # Skip unbalanced reactions
    if(base_reaction not in reactions_dict or 'OK' not in reactions_dict[base_reaction]['status']):
        print("Skipping unbalanced reaction: "+base_reaction)
        continue
    
    # Skip plastidial ATP synthase, need to define additional thylakoid compartment
    # Skip vacuolar ATP synthase too, not sure how to define intra-vacuolar compartment
    if(base_reaction == "rxn08173" and ('d' in reaction_cpts or 'v' in reaction_cpts)):
        print("Skipping plastidial ATP synthase")
        continue

    # Skip ubiquinol oxidase for now
    # https://en.wikipedia.org/wiki/Alternative_oxidase
    # https://www.annualreviews.org/doi/full/10.1146/annurev-arplant-042110-103857
    # It allows the TCA cycle to continue via succinate dehydrogenase
    # without translocating protons and producing ATP, which causes problems with FBA
    if(base_reaction == "rxn12494"):
        print("Skipping alternative ubiquinol oxidase")
        continue

    # Accordingly, the compartments should all be sorted
    # So a compartment index of 0 matches the first position in the compartment list
    # The order is curated in the PlantSEED database

    reaction_cpt_id = reaction_cpts[0]

    # If its a transporter, need to update the reaction compartment id
    if(len(reaction_cpts)==2):

	# The rule is that it is always the non-cytosolic compartment
        if('c' in reaction_cpts):
            for cpt in reaction_cpts:
                if(cpt != 'c'):
                    reaction_cpt_id = cpt

        # With two main exceptions:
        # 1) whether its an extracellular transporter
        if('e' in reaction_cpts):
            for cpt in reaction_cpts:
                if(cpt != 'e'):
                    reaction_cpt_id = cpt

	# 2) whether its an intraorganellar transporter
        if('j' in reaction_cpts):
            reaction_cpt_id = 'j'

    #determine reaction direction
    direction = "="
    if(reactions_dict[base_reaction]['reversibility'] != "?"):
        direction = reactions_dict[base_reaction]['reversibility']

    if(base_reaction in curated_reactions_dict):
        direction = curated_reactions_dict[base_reaction]

    gapfilling_direction = "="
    if(base_reaction in limited_gf_reactions_list):
        gapfilling_direction = direction

    template_reaction_hash = { 'id':base_reaction+"_"+reaction_cpt_id, 'name':reactions_dict[base_reaction]['name'],
                               'templatecompartment_ref':"~/compartments/id/"+reaction_cpt_id,
                               'reaction_ref':biochem_ref+"/reactions/id/"+base_reaction,
                               'type':"gapfilling", # <------------GAPFILLING
                               'direction':direction,
                               'GapfillDirection':gapfilling_direction,
                               'maxforflux':0.0, 'maxrevflux':0.0,
                               'templateReactionReagents':[], 'templatecomplex_refs':[] }

    # Add reagents
    for entry in (reactions_dict[base_reaction]['stoichiometry'].split(';')):
        (coefficient,compound,gen_cpt,index,name)=entry.split(":",maxsplit=4)
        
        # The generic compartment (gen_cpt) is an indice
        # The reaction compartments (reaction_cpts) generally consist of one compartment
        #    so the indice is 0
        # but in the case of a transporter, the reaction can have multiple compartments
        #    so the indice may be 0, 1, or even 2 in rare cases
        # if the indice is too "high" for the number of reaction compartments, then the
        # reaction is not fully curated, and we default to the highest possible
        if(int(gen_cpt) >= len(reaction_cpts)):
            print("Warning; indice too high: ",base_reaction+"_"+reaction_cpt_id,reaction_cpts,entry)
            gen_cpt = len(reaction_cpts)-1
        rgt_cpt=reaction_cpts[int(gen_cpt)]

        # Check and extend list of template compartments
        if(rgt_cpt not in check_tpl_cpt_dict):
            check_tpl_cpt_dict[rgt_cpt]=1
            plantseed_template_obj['compartments'].append(compartments[rgt_cpt])

        # Check and extend list of template compounds
        if(compound not in check_tpl_cpd_dict):
            check_tpl_cpd_dict[compound]=1
            plantseed_template_obj['compounds'].append(compounds_dict[compound])

        # Check and extend list of template compcompounds
        comp_compound = compound+"_"+rgt_cpt
        if(comp_compound not in check_tpl_cpcpd_dict):
            check_tpl_cpcpd_dict[comp_compound]=1

            comp_compound_hash = { 'id':comp_compound,
                                   'charge':compounds_dict[compound]["defaultCharge"], 'maxuptake':0.0,
                                   'templatecompound_ref':"~/compounds/id/"+compound,
                                   'templatecompartment_ref':"~/compartments/id/"+rgt_cpt };

            plantseed_template_obj['compcompounds'].append(comp_compound_hash)

        rxn_rgt_hash = { 'templatecompcompound_ref' : "~/compcompounds/id/"+comp_compound,
                         'coefficient' : float(coefficient) }
        template_reaction_hash['templateReactionReagents'].append(rxn_rgt_hash)

    plantseed_template_obj['reactions'].append(template_reaction_hash)

#Save Template
with open("PlantSEED_Gapfilling_Template.json",'w') as ps_tmpl_fh:
    json.dump(plantseed_template_obj,ps_tmpl_fh,indent=4)
