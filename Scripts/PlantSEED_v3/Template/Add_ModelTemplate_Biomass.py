#!/usr/bin/env python
from urllib.request import urlopen
import sys
import json
import string

biomass_hash = {'id' : "bio1",
               'name' : "Plant Leaf (Core)",
               'type' : "defaultGrowth",
               'templateBiomassComponents' : []}

compound_type_list = ["other","dna","rna","protein","lipid","cellwall","cofactor","energy"]
for compound_type in compound_type_list:
    biomass_hash[compound_type]=0

with open("../../../Data/PlantSEED_v3/Biomass/PlantSEED_Biomass.txt") as biomass_fh:
    for line in biomass_fh.readlines():
        line=line.strip('\r\n')
        if(line == "" or line[0] == " "):
            continue

        if(line[0] == '#'):
            continue

    
        array = line.split("\t")

        coefficient = 0.0-float(array[3])
        if(coefficient > -1e-4 and coefficient < 0):
            coefficient = -1e-4

        
        tmpbiocpd_hash = { 'class' : array[5],
                           'templatecompcompound_ref' : "~/compcompounds/id/"+array[1]+"_"+array[2],
                           'coefficient_type' : "EXACT",
                           'coefficient' : coefficient,
                           'linked_compound_refs' : [],
                           'link_coefficients' : [] }
        biomass_hash['templateBiomassComponents'].append(tmpbiocpd_hash)

tmpbiomasscpd_hash = { 'class' : 'other',
                       'templatecompcompound_ref' : "~/compcompounds/id/cpd11416_c",
                       'coefficient_type' : "EXACT",
                       'coefficient' : 1,
                       'linked_compound_refs' : [],
                       'link_coefficients' : [] }
biomass_hash['templateBiomassComponents'].append(tmpbiomasscpd_hash)

with open("PlantSEED_Neutral_Template.json") as template_file:
    plantseed_template_obj = json.load(template_file)

#Adding biomass compound to template
biochem_ref = "48/8/1" #AppDev reference
compound_hash = { 'id' : "cpd11416",
                  'compound_ref' : biochem_ref+"/compounds/id/cpd11416",
                  'name' : "Biomass", 'abbreviation' : "Biomass", 'aliases' : [],
                  'formula' : "R", 'isCofactor' : 0,
                  'defaultCharge' : 0.0, 'mass' : 0,
                  'deltaG' : 10000000.0, 'deltaGErr' : 1000000.0 }

cmpcompound_hash = { 'id' : "cpd11416_c",
                     'charge' : 0.0, 'maxuptake' : 0,
                     'templatecompound_ref' : "~/compounds/id/cpd11416",
                     'templatecompartment_ref' : "~/compartments/id/c" }

plantseed_template_obj['compounds'].append(compound_hash)
plantseed_template_obj['compcompounds'].append(cmpcompound_hash)
plantseed_template_obj['biomasses'].append(biomass_hash)

#Save Template
with open("PlantSEED_Biomass_Template.json",'w') as ps_tmpl_fh:
    json.dump(plantseed_template_obj,ps_tmpl_fh,indent=4)
