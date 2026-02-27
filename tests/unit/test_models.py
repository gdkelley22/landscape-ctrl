"""
Unit tests for Pydantic response models (api/models.py).
"""

import pytest
from landscape_ctrl.api.models import Computer, NetworkInterface, Package, Script


class TestComputerModel:
    def test_minimal(self):
        c = Computer.model_validate({"id": 1})
        assert c.id == 1
        assert c.hostname == ""
        assert c.tags == []

    def test_full(self):
        data = {
            "id": 42,
            "hostname": "db-01.example.com",
            "distribution": "Ubuntu 22.04 LTS",
            "tags": ["production", "db-servers"],
            "reboot_required": True,
            "network_interfaces": [
                {
                    "name": "eth0",
                    "ip_addresses": ["192.168.1.10", "10.0.0.10"],
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                }
            ],
        }
        c = Computer.model_validate(data)
        assert c.id == 42
        assert c.hostname == "db-01.example.com"
        assert "production" in c.tags
        assert c.reboot_required is True
        assert c.ip == "192.168.1.10"

    def test_ip_empty_when_no_interfaces(self):
        c = Computer.model_validate({"id": 1})
        assert c.ip == ""

    def test_ip_empty_when_interface_has_no_ips(self):
        c = Computer.model_validate({
            "id": 1,
            "network_interfaces": [{"name": "lo", "ip_addresses": [], "mac_address": ""}],
        })
        assert c.ip == ""


class TestPackageModel:
    def test_defaults(self):
        p = Package.model_validate({"name": "nginx"})
        assert p.name == "nginx"
        assert p.version == ""
        assert p.upgrade is False
        assert p.security is False

    def test_security_upgrade(self):
        p = Package.model_validate({"name": "openssl", "upgrade": True, "security": True})
        assert p.upgrade is True
        assert p.security is True


class TestScriptModel:
    def test_basic(self):
        s = Script.model_validate({"id": 7, "title": "My Script", "interpreter": "/bin/bash"})
        assert s.id == 7
        assert s.title == "My Script"
        assert s.interpreter == "/bin/bash"
