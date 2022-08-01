#!/usr/bin/env python

# import biokbase.workspace.baseclient as baseclient
from biokbase.workspace.client import Workspace

import os, json, sys, time

Workspace_URL = 'https://appdev.kbase.us/services/ws'
# Token = ''
WS_Name = "tcontant:narrative_1626281518370"

WSClient = Workspace(url = Workspace_URL , token = Token)
print('WS Client instantiated: Version '+WSClient.ver())


with open('../Template/PlantSEED_Neutral_Template.json') as json_file:
    Template = json.load(json_file)

    # remove reference to be able to access orginial genome files
    # del(Genome['gff_handle_ref'])

    # save genome to KBase narrative
    WSClient.save_objects({'workspace': WS_Name, 'objects':[{'name': 'Template_Athaliana_GLS_1.0',
                                                            'type': 'KBaseFBA.NewModelTemplate',
                                                            'data': Template}]})


