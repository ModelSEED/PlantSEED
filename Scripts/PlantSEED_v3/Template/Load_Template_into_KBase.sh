#!/bin/bash
echo $KB_AUTH_TOKEN
ws-url https://appdev.kbase.us/services/ws
ws-load KBaseFBA.NewModelTemplate PlantModelTemplate PlantSEED_Gapfilling_Template.json -w NewKBaseModelTemplates
