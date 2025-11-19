#!/usr/bin/env python
from cobrakbase.core.kbase_object_factory import KBaseObjectFactory

KBOF = KBaseObjectFactory()
model = KBOF.build_object_from_file('test_model.json', "KBaseFBA.FBAModel")
media = KBOF.build_object_from_file('PlantAutotrophicMedia.json', "KBaseBiochem.Media")
model.medium = media

sol = model.optimize()
print(sol)
