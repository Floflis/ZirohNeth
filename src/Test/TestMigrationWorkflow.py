import copy
import io
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

# MigrationWorkflow imports the application Config singleton. These focused
# unit tests do not boot the full application/test conftest, so provide only
# the inert config object required at module import time.
if "Config" not in sys.modules:
    config_module = ModuleType("Config")
    config_module.config = SimpleNamespace(openssl_lib_file=None)
    sys.modules["Config"] = config_module

from eth_account import Account

from Crypt import CryptBitcoin, CryptMigration, CryptHash
from Crypt import MigrationWorkflow
from Crypt.MigrationWorkflow import _copy_manifest_files, _migration_journal, MigrationWorkflowError


class _Storage:
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
        manifest["signers_sign"] = CryptBitcoin.sign("1:" + self.address, self.bitcoin_key)
        manifest["signs"] = {
            self.address: CryptBitcoin.sign(json.dumps(manifest, sort_keys=True), self.bitcoin_key)
        }
        return manifest

    def isValidRelativePath(self, path):
        return ".." not in path.parts and not path.is_absolute()


class _Site:
    def __init__(self, address, bitcoin_key):
        self.address = address
        self.storage = _Storage()
        self.storage.address = address
        self.content_manager = _ContentManager(address, bitcoin_key)


def test_prepare_embeds_both_signatures_in_the_final_bitcoin_manifest():
    bitcoin_key = CryptBitcoin.newPrivatekey()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    ethereum = Account.create()
    site = _Site(old_identity, bitcoin_key)

    manifest, record = MigrationWorkflow.prepare_migration(
        site, bitcoin_key, "eth:" + ethereum.key.hex()
    )

    assert manifest["migration"] == record
    assert set(manifest["files"]) == {"index.html"}
    landing_page = CryptMigration.build_migration_landing_page(
        old_identity, record["new_identity"]
    )
    assert manifest["files"]["index.html"]["sha512"] == CryptHash.sha512sum(
        io.BytesIO(landing_page)
    )
    assert manifest["files"]["index.html"]["size"] == len(landing_page)
    assert manifest["migration_source_manifest_digest"] == CryptMigration.legacy_manifest_digest(
        site.storage.loadJson("content.json")
    )
    assert record["old_identity"] == old_identity
    assert record["new_identity"] == ethereum.address
    assert CryptMigration.verify_migration(record)
    assert CryptMigration.verify_final_legacy_manifest(record, manifest)

    # The normal Bitcoin content signature covers the embedded proof too.
    protected = copy.deepcopy(manifest)
    protected.pop("signs")
    assert CryptBitcoin.verify(
        json.dumps(protected, sort_keys=True),
        old_identity,
        manifest["signs"][old_identity],
    )


def test_embedded_migration_proof_is_invalidated_by_manifest_or_record_tampering():
    bitcoin_key = CryptBitcoin.newPrivatekey()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    ethereum = Account.create()
    site = _Site(old_identity, bitcoin_key)
    manifest, record = MigrationWorkflow.prepare_migration(
        site, bitcoin_key, "eth:" + ethereum.key.hex()
    )

    changed = copy.deepcopy(manifest)
    changed["migration"]["new_identity"] = Account.create().address
    assert not CryptMigration.verify_final_legacy_manifest(record, changed)

    changed = copy.deepcopy(manifest)
    changed["title"] = "tampered"
    assert not CryptMigration.verify_final_legacy_manifest(record, changed)



def _source_site(directory):
    return SimpleNamespace(
        storage=SimpleNamespace(directory=Path(directory)),
        content_manager=SimpleNamespace(isValidRelativePath=lambda path: True),
    )


def test_migration_copies_only_legacy_digest_verified_bytes(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    original = b"authenticated legacy bytes"
    (source / "index.html").write_bytes(original)
    manifest = {
        "files": {
            "index.html": {
                "sha512": CryptHash.sha512sum(io.BytesIO(original)),
                "size": len(original),
            }
        }
    }

    _copy_manifest_files(
        _source_site(source),
        SimpleNamespace(storage=SimpleNamespace(directory=target)),
        manifest,
    )

    assert (target / "index.html").read_bytes() == original


def test_migration_rejects_tampered_legacy_file_before_v2_import(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    original = b"the bytes authorized by bitcoin"
    (source / "index.html").write_bytes(b"tampered bytes")
    manifest = {
        "files": {
            "index.html": {
                "sha512": CryptHash.sha512sum(io.BytesIO(original)),
                "size": len(original),
            }
        }
    }

    with pytest.raises(MigrationWorkflowError, match="digest mismatch"):
        _copy_manifest_files(
            _source_site(source),
            SimpleNamespace(storage=SimpleNamespace(directory=target)),
            manifest,
        )

    assert not (target / "index.html").exists()


def test_migration_rejects_missing_required_legacy_file(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    manifest = {"files": {"index.html": {"sha512": "00" * 32, "size": 0}}}

    with pytest.raises(MigrationWorkflowError, match="Required site file is missing"):
        _copy_manifest_files(
            _source_site(source),
            SimpleNamespace(storage=SimpleNamespace(directory=target)),
            manifest,
        )



def test_migration_journal_binds_protocol_source_destination_and_proof():
    bitcoin_key = CryptBitcoin.newPrivatekey()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    ethereum = Account.create()
    site = _Site(old_identity, bitcoin_key)
    _manifest, record = MigrationWorkflow.prepare_migration(
        site, bitcoin_key, "eth:" + ethereum.key.hex()
    )

    journal = _migration_journal(record)
    assert journal["protocol"] == CryptMigration.PROTOCOL_V2
    assert journal["source_identity"] == old_identity
    assert journal["destination_identity"] == ethereum.address
    assert journal["proof_digest"] == CryptMigration.record_digest(record)

    changed = copy.deepcopy(record)
    changed["migration_sequence"] += 1
    assert _migration_journal(changed) != journal



def test_migration_skips_missing_optional_legacy_files(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    manifest = {
        "files": {},
        "files_optional": {
            "optional.bin": {"sha512": "00" * 32, "size": 100}
        },
    }

    _copy_manifest_files(
        _source_site(source),
        SimpleNamespace(storage=SimpleNamespace(directory=target)),
        manifest,
    )

    assert list(target.iterdir()) == []



def test_classic_landing_page_is_deterministic_and_escapes_identity_text():
    page = CryptMigration.build_migration_landing_page(
        '<old&identity>', '0x<new&identity>'
    )
    assert b"This site has migrated" in page
    assert b"https://github.com/ZeroNetPlus/ZirohNeth" in page
    assert b"&lt;old&amp;identity&gt;" in page
    assert b"0x&lt;new&amp;identity&gt;" in page
    assert page == CryptMigration.build_migration_landing_page(
        '<old&identity>', '0x<new&identity>'
    )



def test_verify_imported_source_files_requires_complete_byte_identical_v2_copy(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    original = b"original v1 asset"
    (source / "asset.bin").write_bytes(original)
    (target / "asset.bin").write_bytes(original)
    manifest = {
        "files": {
            "asset.bin": {
                "sha512": CryptHash.sha512sum(io.BytesIO(original)),
                "size": len(original),
            }
        }
    }
    source_site = _source_site(source)
    target_site = SimpleNamespace(storage=SimpleNamespace(directory=target))

    MigrationWorkflow._verify_imported_source_files(source_site, target_site, manifest)

    (target / "asset.bin").write_bytes(b"changed")
    with pytest.raises(MigrationWorkflowError, match="does not preserve original file bytes"):
        MigrationWorkflow._verify_imported_source_files(source_site, target_site, manifest)
