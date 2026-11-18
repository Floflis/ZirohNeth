"""Two-phase Bitcoin -> Ethereum migration orchestration.

The cryptographic proof is protocol-native. Publishing and Ethereum-site
registration are injected adapters because the project has not selected a
global checkpoint registry or EVM network yet.
"""
from pathlib import Path

from Config import config
from Crypt import CryptEthereum
from Crypt import CryptMigration


class MigrationWorkflowError(CryptMigration.MigrationError):
    """Raised when a migration cannot safely advance to the next phase."""


def prepare_migration(site, bitcoin_private_key, ethereum_private_key):
    """Build, but do not publish, the final Bitcoin manifest and dual proof.

    This function is intentionally side-effect free: callers can inspect and
    persist/export the artifacts before committing the irreversible registry
    operation.
    """
    old_identity = site.address
    if not CryptMigration.CryptBitcoin.isValidAddress(old_identity):
        raise MigrationWorkflowError("The source site is not a legacy Bitcoin identity")

    new_identity = CryptEthereum.normalize_address(
        CryptEthereum.private_key_to_address(ethereum_private_key)
    )
    if old_identity == new_identity:
        raise MigrationWorkflowError("Source and destination identities must differ")

    current = site.storage.loadJson("content.json")
    if current.get("includes") or current.get("user_contents"):
        raise MigrationWorkflowError(
            "Migration with included/user manifests is blocked until their signer lifecycle is supported"
        )

    # Mark the final legacy root explicitly, then sign it with the old key.
    final_manifest = site.content_manager.sign(
        "content.json",
        privatekey=bitcoin_private_key,
        filewrite=False,
        extend={
            "migration_status": "historical",
            "migration_protocol": CryptMigration.PROTOCOL,
            "migration_target": new_identity,
        },
    )
    final_sequence = final_manifest.get("sequence", final_manifest.get("modified"))
    payload = {
        "protocol": CryptMigration.PROTOCOL,
        "old_identity": old_identity,
        "new_identity": new_identity,
        "final_legacy_manifest_digest": CryptMigration.legacy_manifest_digest(final_manifest),
        "final_legacy_sequence": final_sequence,
        "migration_sequence": 1,
        "previous_migration_digest": CryptMigration.ZERO_DIGEST,
    }
    record = CryptMigration.sign_migration(
        payload, bitcoin_private_key, ethereum_private_key
    )
    if not CryptMigration.verify_final_legacy_manifest(record, final_manifest):
        raise MigrationWorkflowError("Generated final legacy manifest did not verify")
    if not CryptMigration.verify_migration(record):
        raise MigrationWorkflowError("Generated dual-signed migration proof did not verify")
    return final_manifest, record


def commit_migration(
    site,
    final_manifest,
    record,
    checkpoint_store,
    publish_checkpoint,
    lookup_checkpoint,
    register_ethereum_site,
):
    """Publish, independently read back, pin, and register a migration.

    Adapter contracts:
      publish_checkpoint(record): publish to the selected global registry.
      lookup_checkpoint(old_identity): fetch the registry's authoritative record.
      register_ethereum_site(record, final_manifest): create/import the new
        Ethereum site and return its registered site object or identifier.

    The registry read-back is mandatory. A successful publish response alone
    is not treated as proof of publication. The function is retryable after a
    registry success because local pinning and site registration are idempotent.
    """
    if not CryptMigration.verify_migration(record):
        raise MigrationWorkflowError("Migration record signatures are invalid")
    if not CryptMigration.verify_final_legacy_manifest(record, final_manifest):
        raise MigrationWorkflowError("Final Bitcoin manifest does not match migration proof")

    old_identity = record["old_identity"]
    new_identity = record["new_identity"]
    expected_store = Path(config.data_dir) / "migration-checkpoints" / (old_identity + ".json")
    if checkpoint_store.path.resolve() != expected_store.resolve():
        raise MigrationWorkflowError("CheckpointStore path must match ContentManager enforcement path")
    if site.address != old_identity:
        raise MigrationWorkflowError("Migration source site does not match old_identity")

    # Persist the terminal legacy manifest first. If publication fails, it can
    # be retried with the same proof; the old identity is not yet locally pinned.
    site.storage.writeJson("content.json", final_manifest)
    site.content_manager.contents["content.json"] = final_manifest
    published_peers = site.publish(inner_path="content.json")
    if not published_peers:
        raise MigrationWorkflowError("Final Bitcoin manifest was not published to any peer")

    publish_checkpoint(record)
    published = lookup_checkpoint(old_identity)
    if not published or CryptMigration.record_digest(published) != CryptMigration.record_digest(record):
        raise MigrationWorkflowError("Registry read-back does not match the published migration record")

    expected_digest = CryptMigration.record_digest(record)
    latest = checkpoint_store.latest()
    if latest is None:
        checkpoint_store.trust_checkpoint(record, expected_digest)
    elif CryptMigration.record_digest(latest) != expected_digest:
        checkpoint_store.append(record)

    # Keep the old address and its files intact. The checkpoint guard prevents
    # later non-terminal root manifests from being accepted by aware clients.
    site.settings["migration_role"] = "historical"
    site.settings["migration_target"] = new_identity
    site.settings["migration_checkpoint"] = expected_digest
    site.saveSettings()

    # Registration is deliberately last. If it fails, the checkpoint remains
    # authoritative and this function can be retried to finish registration.
    return register_ethereum_site(record, final_manifest)
