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

WS_Name = "seaver:narrative_1667322337892"
WS_Object = "Phytozome_Athaliana_TAIR10"
Data_Object = WSClient.get_objects2({'objects':[{'workspace':WS_Name,'name':WS_Object}]})['data'][0]['data']

with open(WS_Object+".json",'w') as fh:
	fh.write(json.dumps(Data_Object))
