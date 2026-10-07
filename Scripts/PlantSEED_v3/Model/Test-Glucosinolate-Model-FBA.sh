#!/bin/sh
# Run FBA on the Arabidopsis model with all 22 PlantSEED glucosinolates
# loaded into the biomass objective. Thin wrapper over the generalized
# Test-Model-Biomass-with-FBA.py -- see that script and biomass_loader.py
# for how any other biomass file can be tested the same way.
exec python Test-Model-Biomass-with-FBA.py \
	--biomass-file ../../../Data/PlantSEED_v3/Biomass/plantseed-glucosinolate-biomass.txt \
	"$@"
