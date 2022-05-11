#!/usr/bin/env python

#Setting up environment
from biokbase.workspace.client import Workspace
import os, json, sys, time
Token = os.environ['KB_AUTH_TOKEN']
Workspace_URL = 'https://kbase.us/services/ws'
WSClient = Workspace(url = Workspace_URL, token = Token)
#############################################
print('WS Client instantiated: Version '+WSClient.ver())

# The name of the narrative and the workspace are stored as a single varibale
# Defining the name of the underlying workspace makes it easier to cross-reference
# when writing scripts that handle workspace objects
New_WS_Name="noname"
print("Edit for new workspace name!")
sys.exit()

# Set metadata for workspace itself
workspace_info_meta={"narrative": "1",
                     "narrative_nice_name": New_WS_Name,
                     "is_temporary": "false"}

# Create workspace
WSClient.create_workspace({'workspace':New_WS_Name,'meta':workspace_info_meta})

# Old code for following convention of narrative names
# Milliseconds = int(round(time.time() * 1000))
# New_Narrative_Name = "Narrative."+str(Milliseconds)

# Create meta data that goes into the Narrative object
narrative_meta = {"creator" : "seaver",
                  "ws_name" : New_WS_Name,
                  "name" : New_WS_Name,
                  "description" : "",
                  "data_dependencies" : [],
                  "format" : "ipynb",
                  "type" : "KBaseNarrative.Narrative"}

# Create empty narrative object with meta data
Empty_Narrative = {"nbformat" : 4,
                   "nbformat_minor" : 1,
                   "cells" : [],
                   "metadata":narrative_meta}

# Create user meta data for workspace object
narrative_user_meta = {"creator" : "seaver",
                       "ws_name" : New_WS_Name,
                       "name" : New_WS_Name,
                       "description" : "",
                       "type" : "KBaseNarrative.Narrative",
                       "is_temporary": "false"}

# Save empty narrative object along with user meta data
save_object_dict={"type":"KBaseNarrative.Narrative",
                  "data":Empty_Narrative,
                  "name":New_WS_Name,
                  "meta":narrative_user_meta}

result = WSClient.save_objects({"workspace":New_WS_Name,"objects":[save_object_dict]})

# as far as I understand, all of the meta data is necessary for either saving the Narrative workspace object
# or for getting it to appear and behave normally in the Narrative Navigator at https://narrative.kbase.us
