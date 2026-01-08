#!/usr/bin/env python

#Setting up environment
#from Workspace.WorkspaceClient import Workspace as Workspace
import biokbase.workspace.baseclient as baseclient
from biokbase.workspace.client import Workspace

import os, json, sys, time
Workspace_URL = 'https://kbase.us/services/ws'
Token = os.environ['KB_AUTH_TOKEN']
WSClient = Workspace(url = Workspace_URL, token = Token)
#############################################
print('WS Client instantiated: Version '+WSClient.ver())

Workspace = 'Phytozome_Genomes'
Workspace = 'Photosynthetic_FBA_Tutorial'
Workspace = 'NewKBaseModelTemplates'
Workspace = 'Full_Plant_Reconstructions'

Result_List = WSClient.list_objects({'workspaces':[Workspace]}) #,'type':'KBaseGenomes.Genome'})

for result in Result_List:
	row = []
	for entry in result:
		row.append(str(entry))
	print('\t'.join(row))
