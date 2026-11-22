import json
import logging
import re
import os
import time
import atexit

import gevent

import util
from Plugin import PluginManager
from Content import ContentDb
from Config import config
from util import helper
from util import RateLimit
from util import Cached
from Debug import Debug

@PluginManager.acceptPlugins
class SiteManager(object):
    def __init__(self):
        self.log = logging.getLogger("SiteManager")
        self.log.debug("SiteManager created.")
        self.sites = {}
        self.sites_changed = int(time.time())
        self.loaded = False
        gevent.spawn(self.saveTimer)
        atexit.register(lambda: self.save(recalculate_size=True))

    # Load all sites from data/sites.json
    @util.Noparallel()
    def load(self, cleanup=True, startup=False):
        from .Site import Site
        self.log.info(f'Loading sites... ({cleanup=}, {startup=})')
        self.loaded = False
        address_found = []
        added = 0
        load_s = time.time()
        # Load new adresses
        try:
            json_path = config.private_dir / 'sites.json'
            data = json.load(open(json_path))
        except Exception as err:
            self.log.error(f"Unable to load {json_path}: {err}")
            data = {}

        sites_need = []

        for address, settings in data.items():
            address = self.normalizeAddress(address)
            if address not in self.sites:
                if (config.data_dir / address / 'content.json').is_file():
                    # Root content.json exists, try load site
                    s = time.time()
                    try:
                        site = Site(address, settings=settings)
                        site.content_manager.contents.get("content.json")
                        migration_target = self.resolveMigrationAddress(address)
                        if migration_target != address:
                            site.settings["migration_role"] = "historical"
                            site.settings["migration_target"] = migration_target
                    except Exception as err:
                        self.log.debug("Error loading site %s: %s" % (address, err))
                        continue
                    self.sites[address] = site
                    self.log.debug("Loaded site %s in %.3fs" % (address, time.time() - s))
                    added += 1
                elif startup:
                    # No site directory, start download
                    self.log.debug("Found new site in sites.json: %s" % address)
                    sites_need.append([address, settings])
                    added += 1

            address_found.append(address)

        # Remove deleted adresses
        if cleanup:
            for address in list(self.sites.keys()):
                if address not in address_found:
                    del(self.sites[address])
                    self.log.debug("Removed site: %s" % address)

            # Remove orpan sites from contentdb
            content_db = ContentDb.getContentDb()
            for row in content_db.execute("SELECT * FROM site").fetchall():
                address = row["address"]
                if address not in self.sites and address not in address_found:
                    self.log.info("Deleting orphan site from content.db: %s" % address)

                    try:
                        content_db.execute("DELETE FROM site WHERE ?", {"address": address})
                    except Exception as err:
                        self.log.error("Can't delete site %s from content_db: %s" % (address, err))

                    if address in content_db.site_ids:
                        del content_db.site_ids[address]
                    if address in content_db.sites:
                        del content_db.sites[address]

        self.loaded = True
        # A downloaded v2 site may contain a Bitcoin-authorized compatibility
        # manifest. Materialize its historical address only after verifying it.
        for site in list(self.sites.values()):
            try:
                self.registerMigrationCompatibility(site)
            except Exception as err:
                self.log.warning(
                    "Unable to register migration compatibility for %s: %s",
                    site.address, err
                )

        for address, settings in sites_need:
            gevent.spawn(self.need, address, settings=settings)
        if added:
            self.log.info("Added %s sites in %.3fs" % (added, time.time() - load_s))

    def saveDelayed(self):
        RateLimit.callAsync("Save sites.json", allowed_again=5, func=self.save)

    def save(self, recalculate_size=False):
        if not self.sites:
            self.log.debug("Save skipped: No sites found")
            return
        if not self.loaded:
            self.log.debug("Save skipped: Not loaded")
            return
        s = time.time()
        data = {}
        # Generate data file
        s = time.time()
        for address, site in list(self.list().items()):
            if recalculate_size:
                site.settings["size"], site.settings["size_optional"] = site.content_manager.getTotalSize()  # Update site size
            data[address] = site.settings
            data[address]["cache"] = site.getSettingsCache()
        time_generate = time.time() - s

        s = time.time()
        if data:
            helper.atomicWrite(config.private_dir / 'sites.json', helper.jsonDumps(data).encode("utf8"))
        else:
            self.log.debug("Save error: No data")
        time_write = time.time() - s

        # Remove cache from site settings
        for address, site in self.list().items():
            site.settings["cache"] = {}

        self.log.debug("Saved sites in %.2fs (generate: %.2fs, write: %.2fs)" % (time.time() - s, time_generate, time_write))

    def saveTimer(self):
        while 1:
            time.sleep(60 * 10)
            self.save(recalculate_size=True)

    # Checks if its a valid address
    def isAddress(self, address):
        if not isinstance(address, str):
            return False
        if address.startswith("0x"):
            try:
                from Crypt import CryptEthereum
                CryptEthereum.normalize_address(address)
                return True
            except ValueError:
                return False
        return bool(re.fullmatch(r"[A-Za-z0-9]{26,35}", address))

    def normalizeAddress(self, address):
        if isinstance(address, str) and address.startswith("0x"):
            from Crypt import CryptEthereum
            return CryptEthereum.normalize_address(address)
        return address

    def isDomain(self, address):
        return False

    @Cached(timeout=10)
    def isDomainCached(self, address):
        return self.isDomain(address)

    def resolveDomain(self, domain):
        return False

    @Cached(timeout=10)
    def resolveDomainCached(self, domain):
        return self.resolveDomain(domain)

    def resolveMigrationAddress(self, address):
        """Resolve a legacy Bitcoin address from its locally stored signed root manifest."""
        if not self.isAddress(address) or address.startswith("0x"):
            return address
        manifest_path = config.data_dir / address / "content.json"
        if not manifest_path.is_file():
            return address
        try:
            with manifest_path.open("r", encoding="utf-8") as stream:
                manifest = json.load(stream)
            record = manifest.get("migration")
            if not isinstance(record, dict):
                return address
            from Crypt import CryptMigration
            if record.get("old_identity") != address:
                return address
            if not CryptMigration.verify_migration(record):
                return address
            if not CryptMigration.verify_final_legacy_manifest(record, manifest):
                return address
            checkpoint_path = config.data_dir / "migration-checkpoints" / (address + ".json")
            checkpoint_store = CryptMigration.CheckpointStore(checkpoint_path)
            checkpoint = checkpoint_store.latest()
            digest = CryptMigration.record_digest(record)
            if checkpoint and CryptMigration.record_digest(checkpoint) != digest:
                return address
            if not checkpoint:
                checkpoint_store.trust_checkpoint(record, digest)
            return self.normalizeAddress(record["new_identity"])
        except Exception as err:
            self.log.debug("Unable to resolve migration for %s: %s", address, err)
            return address

    def registerMigrationCompatibility(self, site):
        """Expose a verified terminal v1 manifest under its historical address.

        The compatibility file is required and BLAKE3-authenticated by the v2
        root; its embedded migration record and Bitcoin signature are then
        checked independently before the old-address alias is advertised.
        """
        from .Site import Site
        from Crypt import CryptMigration, CryptHash
        import copy
        import io

        try:
            root = site.content_manager.contents.get("content.json")
            if not isinstance(root, dict):
                if not site.storage.isFile("content.json"):
                    return False
                root = site.storage.loadJson("content.json")
            if int(root.get("content_version", 1)) != 2:
                return False

            descriptor = root.get("migration_compatibility")
            if not isinstance(descriptor, dict):
                return False
            if descriptor.get("inner_path") != CryptMigration.COMPATIBILITY_MANIFEST_PATH:
                raise ValueError("Unsupported migration compatibility path")

            # Local cache presence is not proof of authenticity. Re-check the
            # Ethereum EIP-712 root signature after restart before trusting its
            # pointer to the Bitcoin compatibility manifest.
            if site.content_manager.verifyFile(
                "content.json", copy.deepcopy(root), ignore_same=False
            ) is not True:
                raise ValueError("The v2 root signature or content policy is invalid")

            compatibility_path = site.storage.getPath(CryptMigration.COMPATIBILITY_MANIFEST_PATH)
            if not compatibility_path.is_file():
                return False

            # The compatibility object must be a required, BLAKE3-authenticated
            # v2 file, not merely a local JSON file at the reserved path.
            file_info = root.get("files", {}).get(CryptMigration.COMPATIBILITY_MANIFEST_PATH)
            if (
                not isinstance(file_info, dict)
                or "blake3" not in file_info
                or CryptMigration.COMPATIBILITY_MANIFEST_PATH in root.get("files_optional", {})
            ):
                raise ValueError("Compatibility manifest is not a required BLAKE3 v2 file")
            with compatibility_path.open("rb") as stream:
                compatibility_bytes = stream.read()
            actual_digest = CryptHash.blake3sum(io.BytesIO(compatibility_bytes))
            actual_size = len(compatibility_bytes)
            if actual_digest != file_info.get("blake3") or actual_size != file_info.get("size"):
                raise ValueError("Compatibility manifest BLAKE3 digest or size does not match v2 root")

            # Hash and parse the same byte sequence to avoid a read/hash race.
            legacy_manifest = json.loads(compatibility_bytes.decode("utf-8"))

            if not CryptMigration.verify_compatibility_manifest(root, legacy_manifest, site.address):
                raise ValueError("Compatibility manifest failed v2/Bitcoin proof validation")

            # The Classic page is committed by both the Bitcoin SHA-512/size
            # entry and the Ethereum BLAKE3 root.
            page_inner_path = "migration/legacy-index.html"
            page_path = site.storage.getPath(page_inner_path)
            page_info = root.get("files", {}).get(page_inner_path)
            if (
                not isinstance(page_info, dict)
                or page_inner_path in root.get("files_optional", {})
                or not page_path.is_file()
            ):
                raise ValueError("Classic migration page is not a required v2 file")
            landing_page = page_path.read_bytes()
            if (
                CryptHash.blake3sum(io.BytesIO(landing_page)) != page_info.get("blake3")
                or len(landing_page) != page_info.get("size")
            ):
                raise ValueError("Classic migration page failed its v2 BLAKE3 digest/size check")
            legacy_page_info = legacy_manifest.get("files", {}).get("index.html", {})
            if (
                CryptHash.sha512sum(io.BytesIO(landing_page)) != legacy_page_info.get("sha512")
                or len(landing_page) != legacy_page_info.get("size")
                or landing_page != CryptMigration.build_migration_landing_page(
                    legacy_manifest["address"], site.address
                )
            ):
                raise ValueError("Classic migration page does not match the Bitcoin-signed manifest")

            record = legacy_manifest["migration"]
            old_address = record["old_identity"]
            expected_digest = CryptMigration.record_digest(record)
            checkpoint_path = config.data_dir / "migration-checkpoints" / (old_address + ".json")
            checkpoint_store = CryptMigration.CheckpointStore(checkpoint_path)
            checkpoint = checkpoint_store.latest()
            if checkpoint and CryptMigration.record_digest(checkpoint) != expected_digest:
                raise ValueError("Compatibility manifest conflicts with the pinned migration checkpoint")

            legacy_directory = config.data_dir / old_address
            legacy_manifest_path = legacy_directory / "content.json"
            write_legacy_manifest = not legacy_manifest_path.is_file()
            if not write_legacy_manifest:
                try:
                    with legacy_manifest_path.open("r", encoding="utf-8") as stream:
                        existing_legacy = json.load(stream)
                except (OSError, ValueError):
                    existing_legacy = None

                if isinstance(existing_legacy, dict) and existing_legacy.get("migration"):
                    existing_record = existing_legacy.get("migration")
                    if (
                        not CryptMigration.verify_final_legacy_manifest(existing_record, existing_legacy)
                        or CryptMigration.record_digest(existing_record) != expected_digest
                    ):
                        raise ValueError("A different terminal migration manifest is already pinned locally")
                elif isinstance(existing_legacy, dict):
                    existing_sequence = existing_legacy.get("sequence", existing_legacy.get("modified", 0))
                    terminal_sequence = legacy_manifest.get("sequence", legacy_manifest.get("modified", 0))
                    if existing_legacy.get("address", old_address) != old_address:
                        raise ValueError("Historical directory contains a manifest for another identity")
                    if existing_sequence > terminal_sequence or (
                        existing_sequence == terminal_sequence and existing_legacy != legacy_manifest
                    ):
                        raise ValueError("Local legacy manifest is newer or conflicts with the terminal migration")

                    write_legacy_manifest = True
                else:
                    write_legacy_manifest = True

            if not checkpoint:
                checkpoint_store.trust_checkpoint(record, expected_digest)

            if write_legacy_manifest:
                legacy_directory.mkdir(parents=True, exist_ok=True)
                helper.atomicWrite(
                    legacy_manifest_path,
                    json.dumps(legacy_manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
                )

            # Materialize the verified landing page beside the terminal
            # manifest for unmodified ZeroNet Classic clients.
            legacy_directory.mkdir(parents=True, exist_ok=True)
            legacy_index_path = legacy_directory / "index.html"
            if not legacy_index_path.is_file() or legacy_index_path.read_bytes() != landing_page:
                helper.atomicWrite(legacy_index_path, landing_page)

            alias_settings = {
                "own": False,
                "serving": True,
                "permissions": [],
                "migration_role": "historical",
                "migration_state": "migration_verified",
                "migration_target": site.address,
                "migration_checkpoint": expected_digest,
                "migration_compatibility_parent": site.address,
                "migration_compatibility_seed": True,
            }

            alias_site = self.sites.get(old_address)
            if alias_site is None:
                alias_site = Site(old_address, allow_create=False, settings=alias_settings)
                self.sites[old_address] = alias_site
            else:
                alias_site.settings.update(alias_settings)
                # Refresh an already loaded historical site if its older root
                # was safely advanced to the verified terminal manifest.
                if write_legacy_manifest:
                    alias_site.content_manager.loadContent(
                        "content.json", load_includes=False, force=True
                    )

            self.sites_changed = int(time.time())
            self.saveDelayed()

            # Start advertising only when the parent v2 site is currently
            # serving. The alias itself also gates requests on that parent.
            if alias_site.isServing():
                gevent.spawn(alias_site.announce, mode="start", force=True)
            return alias_site
        except Exception as err:
            self.log.warning(
                "Migration compatibility for %s was not advertised: %s",
                getattr(site, "address", "<unknown>"), err
            )
            return False

    # Return: Site object or None if not found
    def get(self, address):
        if self.isAddress(address):
            address = self.normalizeAddress(address)
            address = self.resolveMigrationAddress(address)
        if self.isDomainCached(address):
            address_resolved = self.resolveDomainCached(address)
            if address_resolved:
                address = address_resolved

        if not self.loaded:  # Not loaded yet
            self.log.debug("Loading site: %s)..." % address)
            self.load()
        site = self.sites.get(address)

        return site

    def add(self, address, all_file=True, settings=None, **kwargs):
        from .Site import Site
        if self.isAddress(address):
            address = self.resolveMigrationAddress(self.normalizeAddress(address))
        self.sites_changed = int(time.time())
        # Try to find site with differect case
        for recover_address, recover_site in list(self.sites.items()):
            if recover_address.lower() == address.lower():
                return recover_site

        if not self.isAddress(address):
            return False  # Not address: %s % address
        address = self.normalizeAddress(address)
        self.log.debug("Added new site: %s" % address)
        config.loadTrackersFile()
        site = Site(address, settings=settings)
        self.sites[address] = site
        if not site.settings["serving"]:  # Maybe it was deleted before
            site.settings["serving"] = True
        site.saveSettings()
        if all_file:  # Also download user files on first sync
            site.download(check_size=True, blind_includes=True)
        return site

    # Return or create site and start download site files
    def need(self, address, *args, **kwargs):
        if self.isAddress(address):
            address = self.normalizeAddress(address)
            address = self.resolveMigrationAddress(address)
        if self.isDomainCached(address):
            address_resolved = self.resolveDomainCached(address)
            if address_resolved:
                address = address_resolved

        site = self.get(address)
        if not site:  # Site not exist yet
            site = self.add(address, *args, **kwargs)
        return site

    def delete(self, address):
        self.sites_changed = int(time.time())
        self.log.debug("Deleted site: %s" % address)
        del(self.sites[address])
        # Delete from sites.json
        self.save()

    # Lazy load sites
    def list(self):
        if not self.loaded:  # Not loaded yet
            self.log.debug("Sites not loaded yet...")
            self.load(startup=True)
        return self.sites


site_manager = SiteManager()  # Singletone

if config.action == "main":  # Don't connect / add myself to peerlist
    peer_blacklist = [("127.0.0.1", config.fileserver_port), ("::1", config.fileserver_port)]
else:
    peer_blacklist = []

