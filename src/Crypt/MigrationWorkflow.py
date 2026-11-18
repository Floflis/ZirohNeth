"""Bitcoin -> Ethereum migration discovered from the signed Bitcoin content.json.

The final Bitcoin manifest embeds the dual-signed migration record. No external
registry or peer-provided redirect is trusted. The old identity remains on disk
as a historical alias; SiteManager resolves it to the Ethereum identity after
verifying the embedded proof.
"""
import copy
import json
import shutil
from pathlib import Path

from Config import config
from Crypt import CryptBitcoin, CryptEthereum, CryptMigration


class MigrationWorkflowError(CryptMigration.MigrationError):
    """Raised when a migration cannot safely advance to the next phase."""


def _ethereum_key(private_key):
    if not isinstance(private_key, str):
        raise MigrationWorkflowError("Ethereum private key must be text")
    return private_key if private_key.startswith("eth:") else "eth:" + private_key


def prepare_migration(site, bitcoin_private_key, ethereum_private_key):
    """Create the final Bitcoin manifest with its embedded dual-signed proof."""
    old_identity = site.address
    if not CryptBitcoin.isValidAddress(old_identity):
        raise MigrationWorkflowError("The source site is not a legacy Bitcoin identity")

    eth_key = _ethereum_key(ethereum_private_key)
    new_identity = CryptEthereum.normalize_address(
        CryptEthereum.private_key_to_address(eth_key)
    )
    if old_identity == new_identity:
        raise MigrationWorkflowError("Source and destination identities must differ")

    current = site.storage.loadJson("content.json")
    if not isinstance(current, dict) or int(current.get("content_version", 1)) != 1:
        raise MigrationWorkflowError("Only a legacy v1 root manifest can be migrated")
    if current.get("migration"):
        raise MigrationWorkflowError("This site already has a migration proof")
    if current.get("includes") or current.get("user_contents"):
        raise MigrationWorkflowError(
            "Included/user manifests must be migrated before this site can be transferred"
        )

    # Sign the terminal legacy body once to establish its final sequence and
    # timestamp. The migration envelope is excluded from its body digest to
    # avoid a circular hash, but is covered by the final Bitcoin manifest sig.
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
    record = CryptMigration.sign_migration(payload, bitcoin_private_key, eth_key)

    # Embed the proof and re-sign the complete manifest with the old key.
    final_manifest["migration"] = record
    protected = copy.deepcopy(final_manifest)
    protected.pop("sign", None)
    protected.pop("signs", None)
    signature = CryptBitcoin.sign(json.dumps(protected, sort_keys=True), bitcoin_private_key)
    if not signature:
        raise MigrationWorkflowError("Could not sign the final Bitcoin manifest")
    final_manifest["signs"] = {old_identity: signature}

    if not CryptMigration.verify_migration(record):
        raise MigrationWorkflowError("Generated dual-signed proof did not verify")
    if not CryptMigration.verify_final_legacy_manifest(record, final_manifest):
        raise MigrationWorkflowError("Generated terminal Bitcoin manifest did not verify")
    return final_manifest, record


def _copy_manifest_files(source_site, target_site, manifest):
    """Copy only files authorized by the final root manifest."""
    source_root = source_site.storage.directory.resolve()
    target_root = target_site.storage.directory.resolve()

    for collection_name in ("files", "files_optional"):
        for relative_name in manifest.get(collection_name, {}):
            relative = Path(relative_name)
            if not source_site.content_manager.isValidRelativePath(relative):
                raise MigrationWorkflowError("Unsafe path in final manifest: " + relative_name)
            source = (source_root / relative).resolve()
            target = (target_root / relative).resolve()
            if not source.is_relative_to(source_root) or not target.is_relative_to(target_root):
                raise MigrationWorkflowError("Manifest path escapes the site directory")
            if not source.is_file():
                if collection_name == "files_optional":
                    continue
                raise MigrationWorkflowError("Required site file is missing: " + relative_name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def _register_ethereum_site(site, final_manifest, record, ethereum_private_key, site_manager):
    """Import the old site's files and publish a newly signed Ethereum root."""
    new_identity = record["new_identity"]
    new_site = site_manager.need(new_identity, all_file=False)
    existing_path = new_site.storage.getPath("content.json")

    if existing_path.is_file():
        existing = new_site.storage.loadJson("content.json")
        if (
            existing.get("address") == new_identity
            and int(existing.get("content_version", 1)) == 2
            and new_site.content_manager.verifyFile("content.json", existing, ignore_same=False)
        ):
            new_site.settings["own"] = True
            new_site.settings["serving"] = True
            new_site.saveSettings()
            if not new_site.publish(inner_path="content.json"):
                raise MigrationWorkflowError("Ethereum site manifest could not be published")
            return new_site
        raise MigrationWorkflowError(
            "The Ethereum destination already contains a different or invalid site"
        )
    if any(new_site.storage.directory.iterdir()):
        raise MigrationWorkflowError(
            "The Ethereum destination directory is not empty and has no valid root manifest"
        )

    _copy_manifest_files(site, new_site, final_manifest)

    # Reuse the site's public metadata and file layout, but never carry the
    # Bitcoin identity, old signature, or migration envelope into content v2.
    template = copy.deepcopy(final_manifest)
    for field in (
        "sign", "signs", "signers", "migration", "migration_status",
        "migration_protocol", "migration_target", "content_version",
        "hash_algorithm", "identity_scheme", "signature_scheme",
        "sequence", "previous_update_digest", "signers_sign",
    ):
        template.pop(field, None)
    template["address"] = new_identity
    template["files"] = {}
    template.pop("files_optional", None)
    new_site.storage.writeJson("content.json", template)

    new_site.content_manager.sign(
        "content.json",
        privatekey=_ethereum_key(ethereum_private_key),
        filewrite=True,
        remove_missing_optional=True,
    )
    imported = new_site.storage.loadJson("content.json")
    if not new_site.content_manager.verifyFile("content.json", imported, ignore_same=False):
        raise MigrationWorkflowError("The new Ethereum manifest failed local verification")

    # The new identity is now a normal v2 site. Mark it as locally owned.
    new_site.settings["own"] = True
    new_site.settings["serving"] = True
    new_site.saveSettings()
    if not new_site.publish(inner_path="content.json"):
        raise MigrationWorkflowError("Ethereum site manifest could not be published")
    return new_site


def commit_migration(
    site,
    final_manifest,
    record,
    ethereum_private_key,
    checkpoint_store=None,
    site_manager=None,
):
    """Publish the self-describing final manifest, pin it locally and import Ethereum.

    The manifest itself carries the Bitcoin authorization and Ethereum
    acceptance. A local checkpoint remembers the first verified transition
    and prevents later rollback. Fresh clients cannot detect a peer withholding
    a newer manifest; that limitation is inherent without an external freshness
    oracle and is documented rather than hidden behind a fictitious registry.
    """
    if not CryptMigration.verify_migration(record):
        raise MigrationWorkflowError("Migration record signatures are invalid")
    if not CryptMigration.verify_final_legacy_manifest(record, final_manifest):
        raise MigrationWorkflowError("Final Bitcoin manifest does not embed this migration proof")
    if site.address != record["old_identity"]:
        raise MigrationWorkflowError("Migration source site does not match old_identity")

    if checkpoint_store is None:
        checkpoint_path = Path(config.data_dir) / "migration-checkpoints" / (site.address + ".json")
        checkpoint_store = CryptMigration.CheckpointStore(checkpoint_path)
    if site_manager is None:
        from Site import SiteManager
        site_manager = SiteManager.site_manager

    expected_digest = CryptMigration.record_digest(record)
    latest = checkpoint_store.latest()
    if latest and CryptMigration.record_digest(latest) != expected_digest:
        raise MigrationWorkflowError("A different migration checkpoint is already pinned")

    # Keep the old Bitcoin address and directory intact. Publish its signed
    # terminal manifest before pinning it locally.
    site.storage.writeJson("content.json", final_manifest)
    site.content_manager.contents["content.json"] = final_manifest
    if not site.publish(inner_path="content.json"):
        raise MigrationWorkflowError("Final Bitcoin manifest was not published to any peer")

    if latest is None:
        checkpoint_store.trust_checkpoint(record, expected_digest)

    site.settings["migration_role"] = "historical"
    site.settings["migration_target"] = record["new_identity"]
    site.settings["migration_checkpoint"] = expected_digest
    site.settings["serving"] = True
    site.saveSettings()

    # This step is idempotent: retries reuse an already valid Ethereum site.
    return _register_ethereum_site(
        site, final_manifest, record, ethereum_private_key, site_manager
    )
