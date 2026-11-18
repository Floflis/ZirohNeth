import copy
import json

from eth_account import Account

from Crypt import CryptBitcoin, CryptMigration
from Crypt import MigrationWorkflow


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
