import socket
import struct
import os

import pytest
from util import helper
from Config import config


@pytest.mark.usefixtures("resetSettings")
class TestHelper:
    def testShellquote(self):
        assert helper.shellquote("hel'lo") == "\"hel'lo\""  # Allow '
        assert helper.shellquote('hel"lo') == '"hello"'  # Remove "
        assert helper.shellquote("hel'lo", 'hel"lo') == ('"hel\'lo"', '"hello"')

    def testPackAddress(self):
        for port in [1, 1000, 65535]:
            for ip in ["1.1.1.1", "127.0.0.1", "0.0.0.0", "255.255.255.255", "192.168.1.1"]:
                assert len(helper.packAddress(ip, port)) == 6
                assert helper.unpackAddress(helper.packAddress(ip, port)) == (ip, port)

            for ip in ["1:2:3:4:5:6:7:8", "::1", "2001:19f0:6c01:e76:5400:1ff:fed6:3eca", "2001:4860:4860::8888"]:
                assert len(helper.packAddress(ip, port)) == 18
                assert helper.unpackAddress(helper.packAddress(ip, port)) == (ip, port)

            assert len(helper.packOnionAddress("boot3rdez4rzn36x.onion", port)) == 12
            assert helper.unpackOnionAddress(helper.packOnionAddress("boot3rdez4rzn36x.onion", port)) == ("boot3rdez4rzn36x.onion", port)

        with pytest.raises(struct.error):
            helper.packAddress("1.1.1.1", 100000)

        with pytest.raises(socket.error):
            helper.packAddress("999.1.1.1", 1)

        with pytest.raises(Exception):
            helper.unpackAddress("X")

    def testGetDirname(self):
        assert helper.getDirname("data/users/content.json") == "data/users/"
        assert helper.getDirname("data/users") == "data/"
        assert helper.getDirname("") == ""
        assert helper.getDirname("content.json") == ""
        assert helper.getDirname("data/users/") == "data/users/"
        assert helper.getDirname("/data/users/content.json") == "data/users/"

    def testGetFilename(self):
        assert helper.getFilename("data/users/content.json") == "content.json"
        assert helper.getFilename("data/users") == "users"
        assert helper.getFilename("") == ""
        assert helper.getFilename("content.json") == "content.json"
        assert helper.getFilename("data/users/") == ""
        assert helper.getFilename("/data/users/content.json") == "content.json"

    def testIsIp(self):
        assert helper.isIp("1.2.3.4")
        assert helper.isIp("255.255.255.255")
        assert not helper.isIp("any.host")
        assert not helper.isIp("1.2.3.4.com")
        assert not helper.isIp("1.2.3.4.any.host")

    def testIsPrivateIp(self):
        assert helper.isPrivateIp("192.168.1.1")
        assert not helper.isPrivateIp("1.1.1.1")
        assert helper.isPrivateIp("fe80::44f0:3d0:4e6:637c")
        # Overlay addresses are not local-interface addresses for ZeroNet's
        # reachability heuristic: peers on the same mesh can route to them.
        assert not helper.isPrivateIp("fca5:95d6:bfde:d902:8951:276e:1111:a22c")  # CJDNS
        assert not helper.isPrivateIp("200:1234:5678:9abc::1")  # Yggdrasil

    def testIsMeshIp(self):
        assert helper.isMeshIp("fcab:95d6:bfde:d902:8951:276e:1111:a22c")
        assert helper.isMeshIp("200:1234:5678:9abc::1")
        assert helper.isMeshIp("300:1234:5678:9abc::1")  # Yggdrasil routed prefix
        assert not helper.isMeshIp("2001:db8::1")
        assert not helper.isMeshIp("fd12:3456:789a::1")
        assert not helper.isMeshIp("192.0.2.1")

    def testIpv6RouteProbesIncludeCjdnsAndYggdrasil(self):
        assert "fc00::1" in helper.IPV6_ROUTE_TEST_IPS
        assert "200::1" in helper.IPV6_ROUTE_TEST_IPS

    def testOpenLocked(self):
        locked_f = helper.openLocked(config.data_dir + "/locked.file")
        assert locked_f
        with pytest.raises(BlockingIOError):
            locked_f_again = helper.openLocked(config.data_dir + "/locked.file")
        locked_f_different = helper.openLocked(config.data_dir + "/locked_different.file")

        locked_f.close()
        locked_f_different.close()

        os.unlink(locked_f.name)
        os.unlink(locked_f_different.name)
