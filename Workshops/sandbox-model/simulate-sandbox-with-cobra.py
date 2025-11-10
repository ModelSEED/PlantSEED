#!/usr/bin/env python

from cobrakbase.core.kbase_object_factory import KBaseObjectFactory
KBOF = KBaseObjectFactory()

model_path = 'sandbox-model.json'
model = KBOF.build_object_from_file(model_path, "KBaseFBA.FBAModel")

sol=model.optimize()
print(f"Unconstrained production of G3P: {sol.objective_value:.2f}")

# Inducing photorespiration by forcing the model to consume oxygen
reaction = model.reactions.get_by_id('EX_cpd00007_e0')
reaction.upper_bound=-10.0
reaction.lower_bound=-1000.0

sol=model.optimize()
print(f"Photorespiratory-constrained production of G3P: {sol.objective_value:.2f}")

from cobra.flux_analysis import flux_variability_analysis as fva
fva_result=fva(model,fraction_of_optimum=0.75,processes=1)

for rxn,entry in fva_result.iterrows():
    print(f"{rxn}\t{entry['minimum']:.2f}\t{entry['maximum']:.2f}")
