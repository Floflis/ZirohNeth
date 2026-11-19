import copy
import sys
from types import ModuleType, SimpleNamespace

import pytest
from eth_account import Account

if "Config" not in sys.modules:
    config_module = ModuleType("Config")
    config_module.config = SimpleNamespace(openssl_lib_file=None)
    sys.modules["Config"] = config_module

from Crypt import CryptBitcoin, CryptMigration


def _signed(sequence=1, previous=CryptMigration.ZERO_DIGEST, bitcoin_key=None):
    bitcoin_key = bitcoin_key or CryptBitcoin.newPrivatekey()
    ethereum = Account.create()
    payload = {
        "protocol": CryptMigration.PROTOCOL,
        "old_identity": CryptBitcoin.privatekeyToAddress(bitcoin_key),
        "new_identity": ethereum.address,
        "final_legacy_manifest_digest": "0x" + ("11" * 32),
        "final_legacy_sequence": 42,
        "migration_sequence": sequence,
        "previous_migration_digest": previous,
    }
    record = CryptMigration.sign_migration(payload, bitcoin_key, "eth:" + ethereum.key.hex())
    return record


def test_dual_signature_migration_round_trip():
    record = _signed()
    assert CryptMigration.verify_migration(record)
    changed = copy.deepcopy(record)
    changed["final_legacy_sequence"] += 1
    assert not CryptMigration.verify_migration(changed)


def test_both_signatures_are_required():
    record = _signed()
    record.pop("bitcoin_signature")
    assert not CryptMigration.verify_migration(record)
    record = _signed()
    record.pop("ethereum_signature")
    assert not CryptMigration.verify_migration(record)


def test_checkpoint_requires_explicit_trust_anchor(tmp_path):
    record = _signed()
    store = CryptMigration.CheckpointStore(tmp_path / "migration-checkpoints.json")
    with pytest.raises(CryptMigration.MigrationError):
        store.append(record)
    store.trust_checkpoint(record, CryptMigration.record_digest(record))
    assert store.latest() == record
    assert store.is_terminal(record["old_identity"])


def test_checkpoint_rejects_replay_and_accepts_next_link(tmp_path):
    bitcoin_key = CryptBitcoin.newPrivatekey()
    first = _signed(bitcoin_key=bitcoin_key)
    store = CryptMigration.CheckpointStore(tmp_path / "checkpoints.json")
    store.trust_checkpoint(first, CryptMigration.record_digest(first))
    with pytest.raises(CryptMigration.MigrationError):
        store.append(first)

    second = _signed(
        sequence=2,
        previous="0x" + CryptMigration.record_digest(first),
        bitcoin_key=bitcoin_key,
    )
    store.append(second)
    assert store.latest() == second


def test_final_legacy_manifest_is_bound_and_verified():
    import json

    bitcoin_key = CryptBitcoin.newPrivatekey()
    ethereum = Account.create()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    manifest = {
        "address": old_identity,
        "modified": 1700000000,
        "signs_required": 1,
        "signers_sign": CryptBitcoin.sign("1:" + old_identity, bitcoin_key),
        "migration_status": "historical",
        "migration_protocol": CryptMigration.PROTOCOL,
        "migration_target": ethereum.address,
        "files": {"index.html": {"sha512": "ab" * 32, "size": 10}},
    }
    serialized = json.dumps(manifest, sort_keys=True)
    manifest["signs"] = {old_identity: CryptBitcoin.sign(serialized, bitcoin_key)}
    digest = CryptMigration.legacy_manifest_digest(manifest)
    payload = {
        "protocol": CryptMigration.PROTOCOL,
        "old_identity": old_identity,
        "new_identity": ethereum.address,
        "final_legacy_manifest_digest": digest,
        "final_legacy_sequence": manifest["modified"],
        "migration_sequence": 1,
        "previous_migration_digest": CryptMigration.ZERO_DIGEST,
    }
    record = CryptMigration.sign_migration(payload, bitcoin_key, "eth:" + ethereum.key.hex())
    manifest["migration"] = record
    protected = copy.deepcopy(manifest)
    protected.pop("signs")
    manifest["signs"] = {
        old_identity: CryptBitcoin.sign(json.dumps(protected, sort_keys=True), bitcoin_key)
    }
    assert CryptMigration.verify_migration(record)
    assert CryptMigration.verify_final_legacy_manifest(record, manifest)
    manifest["modified"] += 1
    assert not CryptMigration.verify_final_legacy_manifest(record, manifest)



def _signed_v2():
    bitcoin_key = CryptBitcoin.newPrivatekey()
    ethereum = Account.create()
    payload = {
        "protocol": CryptMigration.PROTOCOL_V2,
        "old_identity": CryptBitcoin.privatekeyToAddress(bitcoin_key),
        "new_identity": ethereum.address,
        "final_legacy_manifest_digest": "0x" + ("22" * 32),
        "final_legacy_manifest_digest_algorithm": "sha256",
        "final_legacy_manifest_canonicalization": "rfc8785",
        "migration_payload_digest_algorithm": "blake3-256",
        "canonicalization": "rfc8785",
        "final_legacy_sequence": 77,
        "migration_sequence": 1,
        "previous_migration_digest": CryptMigration.ZERO_DIGEST,
    }
    return CryptMigration.sign_migration(payload, bitcoin_key, "eth:" + ethereum.key.hex())


def test_migration_protocol_v2_round_trip_and_explicit_digest_suite():
    record = _signed_v2()
    assert CryptMigration.verify_migration(record)
    assert record["final_legacy_manifest_digest_algorithm"] == "sha256"
    assert record["final_legacy_manifest_canonicalization"] == "rfc8785"
    assert record["migration_payload_digest_algorithm"] == "blake3-256"
    assert record["canonicalization"] == "rfc8785"

    for field, invalid in (
        ("final_legacy_manifest_digest_algorithm", "sha512"),
        ("final_legacy_manifest_canonicalization", "json-sort-keys"),
        ("migration_payload_digest_algorithm", "sha256"),
        ("canonicalization", "json-sort-keys"),
    ):
        changed = copy.deepcopy(record)
        changed[field] = invalid
        assert not CryptMigration.verify_migration(changed)


def test_migration_protocol_v2_rejects_missing_digest_suite_fields():
    record = _signed_v2()
    record.pop("canonicalization")
    assert not CryptMigration.verify_migration(record)
