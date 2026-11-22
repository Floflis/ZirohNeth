"""Tests for authenticated v1 compatibility-manifest transport."""

import copy
import io
import json
import logging
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

# Keep these focused tests importable without booting the application.
if "Config" not in sys.modules:
    config_module = ModuleType("Config")
    config_module.config = SimpleNamespace(
        openssl_lib_file=None,
        action="main",
        fileserver_port=0,
        data_dir=Path("."),
        private_dir=Path("."),
        admin_pages=[],
    )
    sys.modules["Config"] = config_module

from eth_account import Account

from Crypt import CryptBitcoin, CryptEthereum, CryptMigration, CryptHash
from Crypt import MigrationWorkflow
from Crypt.MigrationWorkflow import _write_compatibility_manifest


class _Storage:
    def __init__(self, address):
        self.address = address

    def loadJson(self, path):
        return {
            "address": self.address,
            "inner_path": "content.json",
            "modified": 1700000000,
            "signs_required": 1,
            "files": {},
        }


class _ContentManager:
    def __init__(self, address, bitcoin_key):
        self.address = address
        self.bitcoin_key = bitcoin_key

    def sign(self, inner_path, privatekey, filewrite=False, extend=None):
        manifest = {
            "address": self.address,
            "inner_path": "content.json",
            "modified": 1700000000,
            "signs_required": 1,
            "files": {},
        }
        manifest.update(extend or {})
        manifest["signers_sign"] = CryptBitcoin.sign(
            "1:" + self.address, self.bitcoin_key
        )
        manifest["signs"] = {
            self.address: CryptBitcoin.sign(
                json.dumps(manifest, sort_keys=True), self.bitcoin_key
            )
        }
        return manifest


class _Site:
    def __init__(self, address, bitcoin_key):
        self.address = address
        self.storage = _Storage(address)
        self.content_manager = _ContentManager(address, bitcoin_key)


def _prepared_migration():
    bitcoin_key = CryptBitcoin.newPrivatekey()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    ethereum = Account.create()
    site = _Site(old_identity, bitcoin_key)
    manifest, record = MigrationWorkflow.prepare_migration(
        site, bitcoin_key, "eth:" + ethereum.key.hex()
    )
    return manifest, record


def _v2_root(legacy_manifest, record, descriptor):
    proof_digest = CryptMigration.record_digest(record)
    return {
        "address": record["new_identity"],
        "content_version": 2,
        "migration": {
            "protocol": record["protocol"],
            "source_identity": record["old_identity"],
            "proof_digest_algorithm": "blake3-256",
            "proof_digest": proof_digest,
        },
        "migration_compatibility": descriptor,
    }


def test_compatibility_manifest_is_written_verbatim_and_idempotently(tmp_path):
    legacy_manifest, record = _prepared_migration()

    descriptor = _write_compatibility_manifest(
        tmp_path, legacy_manifest, record
    )
    path = tmp_path / CryptMigration.COMPATIBILITY_MANIFEST_PATH
    stored = json.loads(path.read_text(encoding="utf-8"))

    assert stored == legacy_manifest
    assert descriptor["inner_path"] == CryptMigration.COMPATIBILITY_MANIFEST_PATH
    assert descriptor["source_identity"] == record["old_identity"]
    assert descriptor["destination_identity"] == record["new_identity"]
    assert descriptor["manifest_digest"] == CryptMigration.compatibility_manifest_digest(
        legacy_manifest
    )

    # Repeating the operation must preserve the exact authorized file.
    assert _write_compatibility_manifest(
        tmp_path, legacy_manifest, record
    ) == descriptor
    assert json.loads(path.read_text(encoding="utf-8")) == legacy_manifest


def test_v2_pointer_requires_matching_v2_and_bitcoin_authorizations():
    legacy_manifest, record = _prepared_migration()
    descriptor = CryptMigration.build_compatibility_descriptor(
        record, legacy_manifest
    )
    v2_manifest = _v2_root(legacy_manifest, record, descriptor)

    assert CryptMigration.verify_compatibility_manifest(
        v2_manifest, legacy_manifest, record["new_identity"]
    )


def test_compatibility_pointer_rejects_wrong_destination_or_proof_digest():
    legacy_manifest, record = _prepared_migration()
    descriptor = CryptMigration.build_compatibility_descriptor(
        record, legacy_manifest
    )
    v2_manifest = _v2_root(legacy_manifest, record, descriptor)

    wrong_destination = copy.deepcopy(v2_manifest)
    wrong_destination["address"] = Account.create().address
    assert not CryptMigration.verify_compatibility_manifest(
        wrong_destination, legacy_manifest, record["new_identity"]
    )

    wrong_proof = copy.deepcopy(v2_manifest)
    wrong_proof["migration"]["proof_digest"] = "0" * 64
    assert not CryptMigration.verify_compatibility_manifest(
        wrong_proof, legacy_manifest, record["new_identity"]
    )

    wrong_pointer = copy.deepcopy(v2_manifest)
    wrong_pointer["migration_compatibility"]["manifest_digest"] = "0" * 64
    assert not CryptMigration.verify_compatibility_manifest(
        wrong_pointer, legacy_manifest, record["new_identity"]
    )


def test_compatibility_pointer_rejects_tampered_terminal_v1_manifest():
    legacy_manifest, record = _prepared_migration()
    descriptor = CryptMigration.build_compatibility_descriptor(
        record, legacy_manifest
    )
    v2_manifest = _v2_root(legacy_manifest, record, descriptor)

    tampered = copy.deepcopy(legacy_manifest)
    tampered["title"] = "peer-controlled replacement"

    assert not CryptMigration.verify_compatibility_manifest(
        v2_manifest, tampered, record["new_identity"]
    )


def test_compatibility_writer_refuses_to_replace_another_manifest(tmp_path):
    legacy_manifest, record = _prepared_migration()
    path = tmp_path / CryptMigration.COMPATIBILITY_MANIFEST_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"address": "attacker"}), encoding="utf-8")

    with pytest.raises(MigrationWorkflow.MigrationWorkflowError):
        _write_compatibility_manifest(tmp_path, legacy_manifest, record)

    assert json.loads(path.read_text(encoding="utf-8")) == {"address": "attacker"}



def test_migration_aware_site_manager_resolves_old_address_from_terminal_manifest(
    tmp_path, monkeypatch
):
    """A client with the terminal manifest locally resolves the old URL to v2."""
    from Site import SiteManager as SiteManagerModule

    legacy_manifest, record = _prepared_migration()
    monkeypatch.setattr(
        SiteManagerModule.config, "data_dir", tmp_path, raising=False
    )

    legacy_directory = tmp_path / record["old_identity"]
    legacy_directory.mkdir()
    (legacy_directory / "content.json").write_text(
        json.dumps(legacy_manifest, sort_keys=True), encoding="utf-8"
    )

    manager = SiteManagerModule.SiteManager.__new__(SiteManagerModule.SiteManager)
    manager.log = logging.getLogger("TestMigrationCompatibility")

    assert manager.resolveMigrationAddress(record["old_identity"]) == record["new_identity"]

    checkpoint = CryptMigration.CheckpointStore(
        tmp_path / "migration-checkpoints" / (record["old_identity"] + ".json")
    ).latest()
    assert checkpoint is not None
    assert CryptMigration.record_digest(checkpoint) == CryptMigration.record_digest(record)



def _signed_v2_compatibility_site(tmp_path, legacy_manifest, record, ethereum_key):
    """Build a real EIP-712-signed v2 root and its required compatibility file."""
    destination = record["new_identity"]
    descriptor = CryptMigration.build_compatibility_descriptor(record, legacy_manifest)
    site_root = tmp_path / destination
    compatibility_path = site_root / CryptMigration.COMPATIBILITY_MANIFEST_PATH
    compatibility_path.parent.mkdir(parents=True)
    serialized = json.dumps(
        legacy_manifest, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    compatibility_path.write_bytes(serialized)
    landing_page = CryptMigration.build_migration_landing_page(
        record["old_identity"], record["new_identity"]
    )
    landing_path = site_root / "migration" / "legacy-index.html"
    landing_path.parent.mkdir(parents=True, exist_ok=True)
    landing_path.write_bytes(landing_page)

    root = {
        "address": destination,
        "inner_path": "content.json",
        "modified": int(time.time()),
        "signs_required": 1,
        "content_version": 2,
        "hash_algorithm": "blake3-256",
        "identity_scheme": CryptEthereum.IDENTITY_SCHEME,
        "signature_scheme": CryptEthereum.SIGNATURE_SCHEME,
        "sequence": 1,
        "previous_update_digest": CryptEthereum.ZERO_DIGEST,
        "migration": {
            "protocol": record["protocol"],
            "source_identity": record["old_identity"],
            "proof_digest_algorithm": "blake3-256",
            "proof_digest": CryptMigration.record_digest(record),
        },
        "migration_compatibility": descriptor,
        "files": {
            CryptMigration.COMPATIBILITY_MANIFEST_PATH: {
                "blake3": CryptHash.blake3sum(io.BytesIO(serialized)),
                "size": len(serialized),
            },
            "migration/legacy-index.html": {
                "blake3": CryptHash.blake3sum(io.BytesIO(landing_page)),
                "size": len(landing_page),
            },
        },
    }
    root["signs"] = {
        destination: CryptEthereum.sign_manifest(
            root, "eth:" + ethereum_key.hex()
        )
    }
    return site_root, root


def test_site_manager_registers_only_a_signed_and_hash_verified_compatibility_seed(
    tmp_path, monkeypatch
):
    """A v2 peer exposes its old Bitcoin address only after all checks pass."""
    import importlib
    from Site import SiteManager as SiteManagerModule

    ethereum_account = Account.create()
    bitcoin_key = CryptBitcoin.newPrivatekey()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    site_source = _Site(old_identity, bitcoin_key)
    legacy_manifest, record = MigrationWorkflow.prepare_migration(
        site_source, bitcoin_key, "eth:" + ethereum_account.key.hex()
    )

    site_root, root = _signed_v2_compatibility_site(
        tmp_path, legacy_manifest, record, ethereum_account.key
    )
    monkeypatch.setattr(
        SiteManagerModule.config, "data_dir", tmp_path, raising=False
    )

    class _ContentManager:
        contents = {"content.json": root}

        def verifyFile(self, inner_path, content, ignore_same=False):
            signature = content["signs"][record["new_identity"]]
            return CryptEthereum.verify_manifest(
                content, signature, record["new_identity"]
            )

    class _Storage:
        directory = site_root

        def getPath(self, inner_path):
            return site_root / Path(*str(inner_path).split("/"))

        def isFile(self, inner_path):
            return self.getPath(inner_path).is_file()

    parent_site = SimpleNamespace(
        address=record["new_identity"],
        content_manager=_ContentManager(),
        storage=_Storage(),
    )

    class _AliasSite:
        def __init__(self, address, allow_create=True, settings=None):
            self.address = address
            self.settings = dict(settings or {})
            self.announced = False

        def isServing(self):
            return True

        def announce(self, *args, **kwargs):
            self.announced = True

    site_module = importlib.import_module("Site.Site")
    monkeypatch.setattr(site_module, "Site", _AliasSite)
    spawned = []
    monkeypatch.setattr(
        SiteManagerModule.gevent,
        "spawn",
        lambda *args, **kwargs: spawned.append((args, kwargs)),
    )

    manager = SiteManagerModule.SiteManager.__new__(SiteManagerModule.SiteManager)
    manager.sites = {record["new_identity"]: parent_site}
    manager.log = logging.getLogger("TestMigrationCompatibility")
    manager.saveDelayed = lambda: None

    alias = manager.registerMigrationCompatibility(parent_site)

    assert alias is manager.sites[record["old_identity"]]
    assert alias.settings["migration_compatibility_parent"] == record["new_identity"]
    assert alias.settings["migration_role"] == "historical"
    stored_legacy = json.loads(
        (tmp_path / record["old_identity"] / "content.json").read_text(
            encoding="utf-8"
        )
    )
    assert stored_legacy == legacy_manifest
    assert (tmp_path / record["old_identity"] / "index.html").read_bytes() == landing_page
    assert len(spawned) == 1


def test_site_manager_does_not_register_a_tampered_compatibility_file(
    tmp_path, monkeypatch
):
    """A signed root cannot make altered local compatibility bytes seedable."""
    import importlib
    from Site import SiteManager as SiteManagerModule

    ethereum_account = Account.create()
    bitcoin_key = CryptBitcoin.newPrivatekey()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    source = _Site(old_identity, bitcoin_key)
    legacy_manifest, record = MigrationWorkflow.prepare_migration(
        source, bitcoin_key, "eth:" + ethereum_account.key.hex()
    )
    site_root, root = _signed_v2_compatibility_site(
        tmp_path, legacy_manifest, record, ethereum_account.key
    )
    (site_root / CryptMigration.COMPATIBILITY_MANIFEST_PATH).write_bytes(
        b'{"address":"tampered"}'
    )
    monkeypatch.setattr(
        SiteManagerModule.config, "data_dir", tmp_path, raising=False
    )

    class _ContentManager:
        contents = {"content.json": root}

        def verifyFile(self, inner_path, content, ignore_same=False):
            signature = content["signs"][record["new_identity"]]
            return CryptEthereum.verify_manifest(
                content, signature, record["new_identity"]
            )

    class _Storage:
        directory = site_root

        def getPath(self, inner_path):
            return site_root / Path(*str(inner_path).split("/"))

        def isFile(self, inner_path):
            return self.getPath(inner_path).is_file()

    parent_site = SimpleNamespace(
        address=record["new_identity"],
        content_manager=_ContentManager(),
        storage=_Storage(),
    )

    class _AliasSite:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Tampered compatibility data must not create an alias")

    site_module = importlib.import_module("Site.Site")
    monkeypatch.setattr(site_module, "Site", _AliasSite)
    monkeypatch.setattr(SiteManagerModule.gevent, "spawn", lambda *args, **kwargs: None)

    manager = SiteManagerModule.SiteManager.__new__(SiteManagerModule.SiteManager)
    manager.sites = {record["new_identity"]: parent_site}
    manager.log = logging.getLogger("TestMigrationCompatibility")
    manager.saveDelayed = lambda: None

    assert manager.registerMigrationCompatibility(parent_site) is False
    assert record["old_identity"] not in manager.sites
    assert not (tmp_path / record["old_identity"] / "content.json").exists()



def test_historical_alias_serving_tracks_parent_and_global_offline_state(monkeypatch):
    """The Bitcoin address is never served when its Ethereum parent is offline."""
    import importlib
    from Site import SiteManager as SiteManagerModule

    site_module = importlib.import_module("Site.Site")
    alias = site_module.Site.__new__(site_module.Site)
    alias.address = "1HistoricalBitcoinAddress"
    alias.settings = {
        "migration_compatibility_parent": "0x0000000000000000000000000000000000000001"
    }

    state = {"serving": True}
    parent = SimpleNamespace(isServing=lambda: state["serving"])
    monkeypatch.setattr(
        SiteManagerModule.site_manager,
        "sites",
        {alias.settings["migration_compatibility_parent"]: parent},
    )
    monkeypatch.setattr(site_module.config, "offline", False, raising=False)

    assert alias.isServing() is True
    state["serving"] = False
    assert alias.isServing() is False

    state["serving"] = True
    monkeypatch.setattr(site_module.config, "offline", True, raising=False)
    assert alias.isServing() is False



def test_site_manager_reports_competing_newer_bitcoin_manifest_without_overwriting_checkpoint(
    tmp_path, monkeypatch
):
    """A later Bitcoin-signed v1 root is a conflict, never a silent replacement."""
    import importlib
    from Site import SiteManager as SiteManagerModule

    ethereum_account = Account.create()
    bitcoin_key = CryptBitcoin.newPrivatekey()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    source = _Site(old_identity, bitcoin_key)
    terminal_manifest, record = MigrationWorkflow.prepare_migration(
        source, bitcoin_key, "eth:" + ethereum_account.key.hex()
    )
    site_root, root = _signed_v2_compatibility_site(
        tmp_path, terminal_manifest, record, ethereum_account.key
    )

    # Simulate a later manifest signed by the same Bitcoin key from another
    # classic client. Its higher sequence must not replace the terminal pin.
    competing = {
        "address": old_identity,
        "inner_path": "content.json",
        "modified": terminal_manifest["modified"] + 1,
        "signs_required": 1,
        "files": {},
    }
    competing["signs"] = {
        old_identity: CryptBitcoin.sign(
            json.dumps(competing, sort_keys=True), bitcoin_key
        )
    }
    legacy_directory = tmp_path / old_identity
    legacy_directory.mkdir()
    competing_path = legacy_directory / "content.json"
    competing_path.write_text(json.dumps(competing), encoding="utf-8")

    monkeypatch.setattr(SiteManagerModule.config, "data_dir", tmp_path, raising=False)

    class _ContentManager:
        contents = {"content.json": root}

        def verifyFile(self, inner_path, content, ignore_same=False):
            signature = content["signs"][record["new_identity"]]
            return CryptEthereum.verify_manifest(
                content, signature, record["new_identity"]
            )

    class _Storage:
        directory = site_root

        def getPath(self, inner_path):
            return site_root / Path(*str(inner_path).split("/"))

        def isFile(self, inner_path):
            return self.getPath(inner_path).is_file()

    parent_site = SimpleNamespace(
        address=record["new_identity"],
        content_manager=_ContentManager(),
        storage=_Storage(),
    )
    manager = SiteManagerModule.SiteManager.__new__(SiteManagerModule.SiteManager)
    manager.sites = {record["new_identity"]: parent_site}
    manager.log = logging.getLogger("TestMigrationCompatibility")
    manager.saveDelayed = lambda: None

    assert manager.registerMigrationCompatibility(parent_site) is False
    assert json.loads(competing_path.read_text(encoding="utf-8")) == competing
    assert old_identity not in manager.sites
    assert not (tmp_path / "migration-checkpoints" / (old_identity + ".json")).exists()
