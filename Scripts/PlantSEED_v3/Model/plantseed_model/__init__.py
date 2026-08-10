"""plantseed_model — template-driven metabolic reconstruction, plus (Phase 1) the
source-agnostic omics integration layer.

`reconstruct.py` was `Scripts/PlantSEED_v3/Model/reconstruct_app_impl.py` until it was
packaged; it is the engine that produced the preprint models and it runs entirely off
KBase. Importing it no longer requires the importlib.spec_from_file_location hack that
`plantseed_annotation.reconstruct_cli` previously carried.

Pure stdlib. cobrapy and modelseedpy live behind the `model` and `msd` extras and are
imported only by code those extras install.

Note for the Phase 3 merge: `plant_fba/lib/plant_fba/plant_fbaImpl.py` contains a second,
drifted implementation of this same algorithm (measured similarity 0.628). Reconcile both
directions before deleting it — see kbase_refactor/reconstruction_delta_260810.md. In
particular this copy has conditional-spontaneous-reaction handling the KBase copy lacks,
and the KBase copy sources compound metadata from ModelSEEDDatabase rather than the template.
"""

from .reconstruct import ReconstructAppImpl

__all__ = ["ReconstructAppImpl"]
