#!/usr/bin/env python

#Setting up environment
#from Workspace.WorkspaceClient import Workspace as Workspace
import biokbase.workspace.baseclient as baseclient
from biokbase.workspace.client import Workspace

import os, json, sys, time
Workspace_URL = 'https://ci.kbase.us/services/ws'
#Token = os.environ['KB_AUTH_TOKEN']
WSClient = Workspace(url = Workspace_URL) #, token = Token)
#############################################
print('WS Client instantiated: Version '+WSClient.ver())

WS_Name = "NewKBaseModelTemplates"
WS_Object = "PlantModelTemplate"
Data_Object = WSClient.get_objects2({'objects':[{'workspace':WS_Name,'name':WS_Object}]})['data'][0]['data']

print(Data_Object['biochemistry_ref'])
