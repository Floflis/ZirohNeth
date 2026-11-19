import time
import io

import pytest

from File import FileServer
from File import FileRequest
from Crypt import CryptHash
from Peer.PeerHashfield import PeerHashfield
from . import Spy


@pytest.mark.usefixtures("resetSettings")
@pytest.mark.usefixtures("resetTempSettings")
class TestPeer:
    def testPing(self, file_server, site, site_temp):
        file_server.sites[site.address] = site
        client = FileServer(file_server.ip, 1545)
        client.sites = {site_temp.address: site_temp}
        site_temp.connection_server = client
        connection = client.getConnection(file_server.ip, 1544)

        # Add file_server as peer to client
        peer_file_server = site_temp.addPeer(file_server.ip, 1544)

        assert peer_file_server.ping() is not None

        assert peer_file_server in site_temp.peers.values()
        peer_file_server.remove()
        assert peer_file_server not in site_temp.peers.values()

        connection.close()
        client.stop()

    def testDownloadFile(self, file_server, site, site_temp):
        file_server.sites[site.address] = site
        client = FileServer(file_server.ip, 1545)
        client.sites = {site_temp.address: site_temp}
        site_temp.connection_server = client
        connection = client.getConnection(file_server.ip, 1544)

        # Add file_server as peer to client
        peer_file_server = site_temp.addPeer(file_server.ip, 1544)

        # Testing streamFile
        buff = peer_file_server.getFile(site_temp.address, "content.json", streaming=True)
        assert b"sign" in buff.getvalue()

        # Testing getFile
        buff = peer_file_server.getFile(site_temp.address, "content.json")
        assert b"sign" in buff.getvalue()

        connection.close()
        client.stop()

    def testHashfield(self, site):
        sample_hash = list(site.content_manager.contents["content.json"]["files_optional"].values())[0]["sha512"]

        site.storage.verifyFiles(quick_check=True)  # Find what optional files we have

        # Check if hashfield has any files
        assert site.content_manager.hashfield
        assert len(site.content_manager.hashfield) > 0

        # Check exsist hash
        assert site.content_manager.hashfield.getHashId(sample_hash) in site.content_manager.hashfield

        # Add new hash
        new_hash = CryptHash.sha512sum(io.BytesIO(b"hello"))
        assert site.content_manager.hashfield.getHashId(new_hash) not in site.content_manager.hashfield
        assert site.content_manager.hashfield.appendHash(new_hash)
        assert not site.content_manager.hashfield.appendHash(new_hash)  # Don't add second time
        assert site.content_manager.hashfield.getHashId(new_hash) in site.content_manager.hashfield

        # Remove new hash
        assert site.content_manager.hashfield.removeHash(new_hash)
        assert site.content_manager.hashfield.getHashId(new_hash) not in site.content_manager.hashfield

    def testHashfieldAlgorithmNamespaces(self):
        field = PeerHashfield()
        sha512_id = field.getHashId("AABB", "sha512")
        blake3_id = field.getHashId("AABB", "blake3")

        # Equal 16-bit prefixes must not alias across digest algorithms.
        assert sha512_id == 0xAABB
        assert blake3_id == 0x1AABB
        assert field.appendHash("AABB", "sha512")
        assert field.appendHash("AABB", "blake3")
        assert field.appendHash("CAFE", "blake3")
        cafe_blake3_id = field.getHashId("CAFE", "blake3")
        assert len(field) == 3
        assert sha512_id in field
        assert blake3_id in field

        payload = field.toProtocolPayload()
        assert payload["hashfield_version"] == 2
        assert payload["hashfields"]["sha512"] == bytes.fromhex("aabb")
        assert payload["hashfields"]["blake3"] == bytes.fromhex("aabbcafe")

        # A v2 peer restores both buckets without endian ambiguity.
        restored = PeerHashfield()
        assert restored.replaceFromProtocol(payload)
        assert sha512_id in restored
        assert blake3_id in restored
        assert cafe_blake3_id in restored

        # A legacy peer receives only an unversioned 16-bit field. The new
        # client must treat it as an ambiguous availability hint in both
        # algorithm namespaces because old clients did not distinguish them.
        legacy = PeerHashfield()
        assert not legacy.replaceFromProtocol({"hashfield_raw": payload["hashfield_raw"]})
        assert sha512_id in legacy
        assert blake3_id in legacy
        assert cafe_blake3_id in legacy
        # Its raw compatibility table is the union of both namespaces.
        assert field.getHashId("CAFE", "sha512") in legacy

        # Raw bytes alone cannot identify the original digest algorithm.
        # The compatibility API therefore preserves them as ambiguous hints.
        legacy_cache = PeerHashfield()
        legacy_cache.replaceFromBytes(payload["hashfield_raw"])
        assert sha512_id in legacy_cache
        assert blake3_id in legacy_cache
        assert cafe_blake3_id in legacy_cache
        assert field.getHashId("CAFE", "sha512") in legacy_cache

        # The persisted cache keeps both algorithm namespaces.
        restored.replaceFromProtocol(payload)
        cached = PeerHashfield()
        cached.replaceFromCache(restored.toCache())
        assert sha512_id in cached
        assert blake3_id in cached

        # Unknown explicit versions must not silently downgrade to v1.
        try:
            cached.replaceFromProtocol({
                "hashfield_version": 3,
                "hashfield_raw": payload["hashfield_raw"]
            })
        except ValueError:
            pass
        else:
            assert False, "Unknown hashfield versions must be rejected"

        # Truncated network-order entries are rejected.
        try:
            cached.replaceFromProtocol({
                "hashfield_version": 2,
                "hashfields": {"sha512": b"\xaa", "blake3": b""}
            })
        except ValueError:
            pass
        else:
            assert False, "Malformed v2 hashfields must be rejected"

    def testHashfieldExchange(self, file_server, site, site_temp):
        server1 = file_server
        server1.sites[site.address] = site
        site.connection_server = server1

        server2 = FileServer(file_server.ip, 1545)
        server2.sites[site_temp.address] = site_temp
        site_temp.connection_server = server2
        site.storage.verifyFiles(quick_check=True)  # Find what optional files we have
        site.content_manager.hashfield.appendHash("FACE", "blake3")
        blake3_id = site.content_manager.hashfield.getHashId("FACE", "blake3")

        # Add file_server as peer to client
        server2_peer1 = site_temp.addPeer(file_server.ip, 1544)

        # Check if hashfield has any files
        assert len(site.content_manager.hashfield) > 0

        # Testing hashfield sync
        assert len(server2_peer1.hashfield) == 0
        assert server2_peer1.updateHashfield()  # Query hashfield from peer
        assert len(server2_peer1.hashfield) > 0
        assert blake3_id in server2_peer1.hashfield

        # Test force push new versioned hashfield
        site_temp.content_manager.hashfield.appendHash("AABB", "sha512")
        site_temp.content_manager.hashfield.appendHash("AABB", "blake3")
        sha512_id = site_temp.content_manager.hashfield.getHashId("AABB", "sha512")
        peer_blake3_id = site_temp.content_manager.hashfield.getHashId("AABB", "blake3")
        server1_peer2 = site.addPeer(file_server.ip, 1545, return_peer=True)
        with Spy.Spy(FileRequest, "route") as requests:
            assert len(server1_peer2.hashfield) == 0
            server2_peer1.sendMyHashfield()
            assert len(server1_peer2.hashfield) == 2
            assert sha512_id in server1_peer2.hashfield
            assert peer_blake3_id in server1_peer2.hashfield
            server2_peer1.sendMyHashfield()  # Hashfield not changed, should be ignored

            assert len(requests) == 1

            time.sleep(0.01)  # To make hashfield change date different

            site_temp.content_manager.hashfield.appendHash("AACC", "sha512")
            server2_peer1.sendMyHashfield()  # Push hashfield

            assert len(server1_peer2.hashfield) == 3
            assert len(requests) == 2

            site_temp.content_manager.hashfield.appendHash("AADD", "blake3")

            assert server1_peer2.updateHashfield(force=True)  # Request hashfield
            assert len(server1_peer2.hashfield) == 4
            assert len(requests) == 3

            assert not server2_peer1.sendMyHashfield()  # Not changed, should be ignored
            assert len(requests) == 3

        server2.stop()

    def testFindHash(self, file_server, site, site_temp):
        file_server.sites[site.address] = site
        client = FileServer(file_server.ip, 1545)
        client.sites = {site_temp.address: site_temp}
        site_temp.connection_server = client

        # Add file_server as peer to client
        peer_file_server = site_temp.addPeer(file_server.ip, 1544)

        assert peer_file_server.findHashIds([1234]) == {}

        # Add fake peer with requred hash
        fake_peer_1 = site.addPeer(file_server.ip_external, 1544)
        fake_peer_1.hashfield.append(1234)
        fake_peer_2 = site.addPeer("1.2.3.5", 1545)
        fake_peer_2.hashfield.append(1234)
        fake_peer_2.hashfield.append(1235)
        fake_peer_3 = site.addPeer("1.2.3.6", 1546)
        fake_peer_3.hashfield.append(1235)
        fake_peer_3.hashfield.append(1236)

        res = peer_file_server.findHashIds([1234, 1235])
        assert sorted(res[1234]) == sorted([(file_server.ip_external, 1544), ("1.2.3.5", 1545)])
        assert sorted(res[1235]) == sorted([("1.2.3.5", 1545), ("1.2.3.6", 1546)])

        # A versioned lookup keeps equal prefixes in separate namespaces.
        blake3_id = PeerHashfield.getHashId("04D2", "blake3")
        fake_peer_3.hashfield.appendHashId(blake3_id)
        res = peer_file_server.findHashIds([blake3_id])
        assert res[blake3_id] == [("1.2.3.6", 1546)]

        # A pre-v2 requester sends only the 16-bit prefix. The new server
        # searches both algorithms and projects the matches back to that ID.
        legacy_res = peer_file_server.request(
            "findHashIds", {"site": site_temp.address, "hash_ids": [1234]}
        )
        assert "hashfield_version" not in legacy_res
        assert 1234 in legacy_res["peers"]
        assert len(legacy_res["peers"][1234]) == 3

        # Test my address adding for both namespaces.
        site.content_manager.hashfield.append(1234)
        site.content_manager.hashfield.appendHashId(blake3_id)

        res = peer_file_server.findHashIds([1234, 1235, blake3_id])
        assert sorted(res[1234]) == sorted([(file_server.ip_external, 1544), ("1.2.3.5", 1545), (file_server.ip, 1544)])
        assert sorted(res[1235]) == sorted([("1.2.3.5", 1545), ("1.2.3.6", 1546)])
        assert sorted(res[blake3_id]) == sorted([("1.2.3.6", 1546), (file_server.ip, 1544)])

        legacy_res = peer_file_server.request(
            "findHashIds", {"site": site_temp.address, "hash_ids": [1234]}
        )
        assert 1234 in legacy_res["my"]
