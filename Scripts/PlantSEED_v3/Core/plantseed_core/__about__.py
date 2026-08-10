"""Single source of truth for the distribution version and the data version.

`__version__` is read by pyproject.toml via [tool.setuptools.dynamic]; do not
duplicate it anywhere else. `DATA_VERSION` tracks Data/PlantSEED_v3/ and moves
independently of the code — a curation-only change bumps DATA_VERSION and
leaves __version__ alone, which is what lets a container pin a code version and
a data version separately.
"""

__version__ = "3.1.0.dev0"

DATA_VERSION = "3.1.0"
