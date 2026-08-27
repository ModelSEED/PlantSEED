"""Path resolution, and the fixture hygiene the rest of the suite depends on.

`plantseed_curation.paths` keeps its constants as module globals refreshed from
the environment, which makes them cheap to read and easy to leave in a bad
state. These tests are about the second half.
"""


def test_tmp_db_does_not_leak_into_later_tests(tmp_db):
    """`tmp_db` repoints module-level path constants; it must put them back.

    It did not: `monkeypatch` is set up before the fixture and torn down after
    it, so refreshing on teardown re-read the still-patched env and left
    `ROLES_FILE` pointing at a deleted tmp_path. Every later test that read the
    real role file saw an empty database, and only a suite added afterwards
    noticed. The undo() is load-bearing; this pins it.
    """
    from plantseed_curation import paths

    assert paths.ROLES_FILE == tmp_db["roles"]      # inside the fixture


def test_paths_point_at_the_real_database_afterwards():
    """Runs after the test above and must see the shipped data, not a tmp dir."""
    import os

    from plantseed_curation import paths

    assert os.path.isfile(paths.ROLES_FILE), paths.ROLES_FILE
    assert "pytest" not in paths.ROLES_FILE
