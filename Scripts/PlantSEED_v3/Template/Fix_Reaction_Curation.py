#!/usr/bin/env python
from urllib.request import urlopen
import sys
import json
import string

with open("../PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

reactions_list=list()
for entry in roles_list:
    for rxn in entry['reactions']:
        if(rxn not in reactions_list):
            reactions_list.append(rxn)

with open("../PlantSEED_Reactions_Curation.json") as curation_file:
    curated_list = json.load(curation_file)

for entry in curated_list:
    if(entry['id'] in reactions_list):
        print(entry['id']+'\t'+entry['direction'])
