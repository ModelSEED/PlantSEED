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
File_Object = "Phytozome_Athaliana_TAIR10.json.annotated"
WS_Object_Name = "Athaliana_TAIR10_Annotated"
WS_Object_Type = "KBaseGenomes.Genome"
with open(File_Object) as json_file:
    Data_Object = json.load(json_file)

    # save genome to KBase narrative
    WSClient.save_objects({'workspace': WS_Name, 'objects':[{'name': WS_Object_Name,
                                                             'type': WS_Object_Type,
                                                             'data': Data_Object}]})


