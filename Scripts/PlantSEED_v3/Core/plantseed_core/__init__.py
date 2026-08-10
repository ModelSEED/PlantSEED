"""plantseed_core — the platform-neutral foundation of PlantSEED v3.

Everything in this package is pure stdlib and knows nothing about KBase,
modelseed.org, CTS, or any other delivery platform. Platform adapters live in
ModelSEED/plantseed-delivery and depend on this package; the dependency never
runs the other way. A CI gate in this repo enforces that by rejecting any
import of installed_clients, cobrakbase, DataFileUtil, KBaseReport,
SDK_CALLBACK_URL or kbutillib under Scripts/PlantSEED_v3/.

Modules land here over Phase 0-1; see the approved plan. The scaffold exists
now so that pyproject.toml has a real package to hang the version off.
"""

from .__about__ import DATA_VERSION, __version__

__all__ = ["__version__", "DATA_VERSION"]
