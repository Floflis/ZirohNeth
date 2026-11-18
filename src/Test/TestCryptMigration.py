import copy

import pytest
from eth_account import Account

from Crypt import CryptBitcoin, CryptMigration


def _signed(sequence=1, previous=CryptMigration.ZERO_DIGEST):
    bitcoin_key = CryptBitcoin.newPrivatekey()
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
    first = _signed()
    store = CryptMigration.CheckpointStore(tmp_path / "checkpoints.json")
    store.trust_checkpoint(first, CryptMigration.record_digest(first))
    with pytest.raises(CryptMigration.MigrationError):
        store.append(first)

    second = _signed(
        sequence=2,
        previous="0x" + CryptMigration.record_digest(first),
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
    assert CryptMigration.verify_migration(record)
    assert CryptMigration.verify_final_legacy_manifest(record, manifest)
    manifest["modified"] += 1
    assert not CryptMigration.verify_final_legacy_manifest(record, manifest)
