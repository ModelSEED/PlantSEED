"""Identity helpers — sanitizers, registry round-trip, atomic_write."""

import json
import os

from plantseed_curation import identity


def test_sanitize_username_keeps_lower_alnum_only():
    assert identity.sanitize_username("Sam Seaver") == "samseaver"
    assert identity.sanitize_username("Vibhav-Setlur_42") == "vibhavsetlur42"
    assert identity.sanitize_username("") == ""


def test_sanitize_filename_drops_path_and_unsafe_chars():
    assert identity.sanitize_filename("../etc/passwd") == "passwd"
    assert identity.sanitize_filename("my file (1).tsv") == "my_file__1_.tsv"


def test_registry_round_trip(tmp_db):
    identity.save_curator_registry({"alice": {"display_name": "Alice", "github_email": "a@x"}})
    assert identity.load_curator_registry() == {
        "alice": {"display_name": "Alice", "github_email": "a@x"}
    }


def test_confirm_curator_registry_only_inserts_new(tmp_db):
    identity.confirm_curator_registry("alice", "Alice", "a@x")
    identity.confirm_curator_registry("alice", "DIFFERENT", "other@x")  # ignored
    reg = identity.load_curator_registry()
    assert reg["alice"]["display_name"] == "Alice"


def test_atomic_write_creates_dir_and_replaces(tmp_path):
    target = os.path.join(str(tmp_path), "nested", "out.txt")
    identity.atomic_write(target, "hello")
    assert open(target).read() == "hello"
    identity.atomic_write(target, "world")
    assert open(target).read() == "world"
    # No stray .tmp files left behind.
    assert not os.path.exists(target + ".tmp")


def test_normalize_existing_dirname_prefers_on_disk_case(tmp_db):
    real_dir = os.path.join(tmp_db["curators"], "Vibhav")
    os.makedirs(real_dir)
    assert identity.normalize_existing_dirname("vibhav") == "Vibhav"
