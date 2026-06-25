# coding: utf-8
from __future__ import annotations, unicode_literals

from helper.molecule import get_vars, infra_hosts

testinfra_hosts = infra_hosts(host_name="instance")

CONNECT = "virsh --connect qemu:///system"

# --- tests -----------------------------------------------------------------


def test_networks_defined(host, get_vars):
    """every non-absent virtual network must be known to libvirt"""
    listing = host.run(f"{CONNECT} net-list --all").stdout
    for net in get_vars.get("virtual_networks", []):
        if net.get("state") == "absent":
            continue
        assert net["name"] in listing


def test_network_xml(host, get_vars):
    """the rendered network XML must carry name and bridge"""
    for net in get_vars.get("virtual_networks", []):
        if net.get("state") == "absent":
            continue
        xml = host.run(f"{CONNECT} net-dumpxml {net['name']}").stdout
        assert f"<name>{net['name']}</name>" in xml
        if net.get("bridge_name"):
            assert net["bridge_name"] in xml
