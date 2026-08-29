"""enzyme.dat: parsing, and the fact that nothing downloads by default.

The download used to be implicit and unverified. Three separate problems in
nine lines: it fired from a packaged code path (which CTS rejects at image
review), it disabled certificate checking entirely, and it treated any
non-empty file as a complete cache. These pin all three.

Nothing here touches the network. The one test that would is marked and
skipped by default.
"""

import os
import ssl

import pytest

from plantseed_curation import expasy, paths

SAMPLE = (
    "ID   1.1.1.1\n"
    "DE   alcohol dehydrogenase.\n"
    "//\n"
    "ID   4.2.1.-\n"
    "DE   a hydro-lyase\n"
    "DE   acting on carbon.\n"
    "//\n"
)


@pytest.fixture
def cache(tmp_path, monkeypatch):
    p = tmp_path / "enzyme.dat"
    monkeypatch.setattr(paths, "ENZYME_DAT_CACHE", str(p))
    return p


class TestParse:
    def test_one_entry_per_block(self, cache):
        cache.write_text(SAMPLE)
        assert len(expasy.parse_enzyme_dat(str(cache))) == 2

    def test_the_label_carries_the_ec_and_is_capitalised(self, cache):
        cache.write_text(SAMPLE)
        first = expasy.parse_enzyme_dat(str(cache))[0]
        assert first == {"label": "Alcohol dehydrogenase (EC 1.1.1.1)",
                         "ec": "1.1.1.1"}

    def test_continuation_lines_are_joined(self, cache):
        cache.write_text(SAMPLE)
        second = expasy.parse_enzyme_dat(str(cache))[1]
        assert second["label"] == "A hydro-lyase acting on carbon (EC 4.2.1.-)"

    def test_blocks_without_an_id_are_skipped(self, cache):
        cache.write_text("DE   orphan description.\n//\n" + SAMPLE)
        assert len(expasy.parse_enzyme_dat(str(cache))) == 2

    def test_latin1_bytes_do_not_raise(self, cache):
        """enzyme.dat is latin-1; decoding it as UTF-8 dies on real entries."""
        cache.write_bytes("ID   1.1.1.1\nDE   caf\xe9 dehydrogenase.\n//\n"
                          .encode("latin-1"))
        assert expasy.parse_enzyme_dat(str(cache))[0]["ec"] == "1.1.1.1"


class TestTheNetworkIsOptIn:
    def test_a_missing_cache_raises_rather_than_downloading(self, cache):
        """The CTS rule: a packaged run must not fetch. The error has to name
        the fix, because it surfaces a long way from anyone who can act."""
        with pytest.raises(FileNotFoundError) as exc:
            expasy.fetch_enzyme_dat()
        msg = str(exc.value)
        assert "does not download by default" in msg
        assert "PLANTSEED_ENZYME_DAT_CACHE" in msg

    def test_an_empty_cache_counts_as_missing(self, cache):
        cache.write_bytes(b"")
        with pytest.raises(FileNotFoundError):
            expasy.fetch_enzyme_dat()

    def test_a_present_cache_is_parsed_without_the_network(self, cache,
                                                           monkeypatch):
        cache.write_text(SAMPLE)

        def forbidden(*a, **kw):
            raise AssertionError("fetch_enzyme_dat reached the network")

        monkeypatch.setattr(expasy, "download_enzyme_dat", forbidden)
        assert len(expasy.fetch_enzyme_dat()) == 2

    def test_download_true_is_what_reaches_the_network(self, cache, monkeypatch):
        calls = []
        monkeypatch.setattr(expasy, "download_enzyme_dat",
                            lambda dest, *a, **kw: (calls.append(dest),
                                                    cache.write_text(SAMPLE))[0])
        assert len(expasy.fetch_enzyme_dat(download=True)) == 2
        assert calls == [str(cache)]

    def test_the_store_does_not_download_by_default(self):
        """start_load_expasy() was a public way to make any process holding a
        DataStore pull 9 MB from ftp.expasy.org."""
        import inspect

        from plantseed_curation.store import DataStore

        assert inspect.signature(
            DataStore.start_load_expasy).parameters["download"].default is False


class TestCertificatesAreVerified:
    def test_the_module_does_not_disable_verification(self):
        """It did: check_hostname = False and verify_mode = CERT_NONE, which
        accepts any certificate — and the result becomes curation vocabulary.
        Verification against ftp.expasy.org works, so there was nothing to
        work around.

        An ast walk, not a grep: the module's own docstring explains what was
        removed and therefore contains the words. Same reason
        test_core_isolation parses rather than searches."""
        import ast

        for node in ast.walk(ast.parse(open(expasy.__file__).read())):
            if isinstance(node, ast.Attribute) and node.attr in (
                    "check_hostname", "verify_mode"):
                raise AssertionError(
                    f"{expasy.__file__} touches ssl context verification")
            if isinstance(node, ast.Attribute) and node.attr == "CERT_NONE":
                raise AssertionError(f"{expasy.__file__} uses ssl.CERT_NONE")

    def test_it_uses_the_default_context(self):
        assert "create_default_context" in open(expasy.__file__).read()

    def test_the_user_agent_is_truthful(self):
        """It claimed to be Mozilla. ExPASy's operators should be able to see
        who is calling."""
        assert "plantseed" in expasy.USER_AGENT
        assert "Mozilla" not in open(expasy.__file__).read()


class TestPartialDownloads:
    def test_a_failed_download_leaves_no_cache(self, cache, monkeypatch):
        """The old check was `missing or zero-size`, so a download that died
        halfway left a truncated file that was never re-fetched and was parsed
        as though complete."""
        def half_then_fail(*a, **kw):
            raise ConnectionResetError("connection reset mid-body")

        monkeypatch.setattr(expasy.urllib.request, "urlopen", half_then_fail)
        with pytest.raises(ConnectionResetError):
            expasy.download_enzyme_dat(str(cache))
        assert not cache.exists()
        assert not [p for p in os.listdir(cache.parent)
                    if p.startswith(".enzyme_dat-")]


@pytest.mark.skipif(os.environ.get("PLANTSEED_TEST_NETWORK") != "1",
                    reason="set PLANTSEED_TEST_NETWORK=1 to hit ftp.expasy.org")
def test_the_real_endpoint_verifies(tmp_path):
    """Opt-in. Pins the claim that disabling verification was unnecessary."""
    import urllib.request

    req = urllib.request.Request(paths.ENZYME_DAT_URL, method="HEAD",
                                 headers={"User-Agent": expasy.USER_AGENT})
    with urllib.request.urlopen(req, context=ssl.create_default_context(),
                                timeout=30) as r:
        assert r.status == 200
