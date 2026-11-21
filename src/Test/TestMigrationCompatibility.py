"""Tests for authenticated v1 compatibility-manifest transport."""

import copy
import io
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

# Keep these focused tests importable without booting the application.
if "Config" not in sys.modules:
    config_module = ModuleType("Config")
    config_module.config = SimpleNamespace(openssl_lib_file=None)
    sys.modules["Config"] = config_module

from eth_account import Account

from Crypt import CryptBitcoin, CryptMigration
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
