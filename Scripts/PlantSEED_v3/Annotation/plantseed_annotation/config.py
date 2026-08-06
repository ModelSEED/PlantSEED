"""Tier configuration — CPU/RAM/refdata targets for the three runtime
environments the annotator supports.

Consumers pick a tier and the dispatch layer sizes work accordingly:

  kbase  — 2 cores, 22 GB RAM, refdata bundle <= 10 GB
           (the KBase SDK worker box; nested SDK calls run serially, no HPC)
  poplar — 8 cores per celery worker, 128 GB RAM, refdata on /kb/data
           (Argonne-side celery worker behind ModelSEED.org; scale by adding
           worker replicas, not by raising per-worker concurrency)
  local  — as-much-as-you-have; refdata bundle downloaded / mounted per user
           (offline dev, local Docker)

See the plan (§Resource picture, §Distribution pipeline) for the tier
rationale.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TierConfig:
    name: str
    cpu_max: int
    ram_gb_max: int
    refdata_gb_max: int
    concurrency: int
    notes: str


KBASE = TierConfig(
    name="kbase",
    cpu_max=2,
    ram_gb_max=22,
    refdata_gb_max=10,
    concurrency=1,
    notes="KBase SDK worker; nested SDK calls run serially; no HPC.",
)

POPLAR = TierConfig(
    name="poplar",
    cpu_max=8,
    ram_gb_max=128,
    refdata_gb_max=200,
    concurrency=8,
    notes="Argonne celery worker behind ModelSEED.org; scale by adding worker replicas.",
)

LOCAL = TierConfig(
    name="local",
    cpu_max=0,          # unbounded
    ram_gb_max=0,       # unbounded
    refdata_gb_max=0,   # unbounded
    concurrency=1,
    notes="Local Docker / dev machine; user provides limits.",
)

BY_NAME = {t.name: t for t in (KBASE, POPLAR, LOCAL)}


def get(name):
    """Return the TierConfig for `name` (kbase|poplar|local)."""
    if name not in BY_NAME:
        raise ValueError(f"unknown tier {name!r} — expected one of {sorted(BY_NAME)}")
    return BY_NAME[name]
