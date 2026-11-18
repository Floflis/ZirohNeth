import json

from eth_account import Account

from Crypt import CryptBitcoin, CryptMigration
from Crypt import MigrationWorkflow


class _Storage:
    def __init__(self):
        self.files = {}

    def writeJson(self, path, content):
        self.files[str(path)] = content


class _ContentManager:
    def __init__(self):
        self.contents = {}


class _Site:
    def __init__(self, address):
        self.address = address
        self.storage = _Storage()
        self.content_manager = _ContentManager()
        self.settings = {}
        self.saved = False

    def saveSettings(self):
        self.saved = True


def _final_manifest_and_record():
    bitcoin_key = CryptBitcoin.newPrivatekey()
    ethereum = Account.create()
    old_identity = CryptBitcoin.privatekeyToAddress(bitcoin_key)
    manifest = {
        "address": old_identity,
        "inner_path": "content.json",
        "modified": 1700000000,
        "files": {},
    }
    manifest["signs"] = {
        old_identity: CryptBitcoin.sign(json.dumps(manifest, sort_keys=True), bitcoin_key)
    }
    payload = {
        "protocol": CryptMigration.PROTOCOL,
        "old_identity": old_identity,
        "new_identity": ethereum.address,
        "final_legacy_manifest_digest": CryptMigration.legacy_manifest_digest(manifest),
        "final_legacy_sequence": manifest["modified"],
        "migration_sequence": 1,
        "previous_migration_digest": CryptMigration.ZERO_DIGEST,
    }
    record = CryptMigration.sign_migration(
        payload, bitcoin_key, "eth:" + ethereum.key.hex()
    )
    return manifest, record


def test_commit_requires_registry_readback_before_local_pin_or_registration(tmp_path):
    manifest, record = _final_manifest_and_record()
    site = _Site(record["old_identity"])
    published = {}
    registered = []

    def publish(item):
        published[item["old_identity"]] = item

    def lookup(identity):
        return None  # Simulate a registry that accepted no durable checkpoint.

    def register(item, final_manifest):
        registered.append(item)
        return "registered"

    store = CryptMigration.CheckpointStore(tmp_path / "checkpoints.json")
    try:
        MigrationWorkflow.commit_migration(
            site, manifest, record, store, publish, lookup, register
        )
    except MigrationWorkflow.MigrationWorkflowError:
        pass
    else:
        raise AssertionError("Registry read-back mismatch must abort migration")

    assert store.latest() is None
    assert not registered
    assert "content.json" in site.storage.files


def test_commit_pins_checkpoint_then_registers_and_can_be_retried(tmp_path):
    manifest, record = _final_manifest_and_record()
    site = _Site(record["old_identity"])
    published = {}
    registered = []

    def publish(item):
        published[item["old_identity"]] = item

    def lookup(identity):
        return published.get(identity)

    def register(item, final_manifest):
        registered.append(item["new_identity"])
        return "ethereum-site"

    store = CryptMigration.CheckpointStore(tmp_path / "checkpoints.json")
    result = MigrationWorkflow.commit_migration(
        site, manifest, record, store, publish, lookup, register
    )

    assert result == "ethereum-site"
    assert store.latest() == record
    assert site.settings["migration_role"] == "historical"
    assert site.settings["migration_target"] == record["new_identity"]
    assert site.saved

    # Repeating the operation must not append a duplicate checkpoint.
    MigrationWorkflow.commit_migration(
        site, manifest, record, store, publish, lookup, register
    )
    assert store.latest() == record
    assert registered == [record["new_identity"], record["new_identity"]]
