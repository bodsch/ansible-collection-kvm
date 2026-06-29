# -*- coding: utf-8 -*-

# (c) 2026, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the bodsch.kvm libvirt role-data filters.

These verify that the role's existing public data models are translated into
valid input for the new modules, by feeding the filter output straight into the
module XML builders.
"""

from __future__ import absolute_import, division, print_function

import os
import sys

# import the filter plugin and the module builders directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "plugins", "filter"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "plugins", "module_utils"))

from libvirt import FilterModule  # noqa: E402
from libvirt_xml import (  # noqa: E402
    DomainXMLBuilder,
    NetworkXMLBuilder,
    VolumeXMLBuilder,
)

f = FilterModule()


# -- network_specs ---------------------------------------------------------

def test_network_specs_nat_dhcp():
    nets = [{
        "name": "vm-network", "mode": "nat", "bridge_name": "virbr-vm",
        "autostart": True, "state": "active", "enable_dhcp": True,
        "dhcp_gateway": "192.168.0.1", "dhcp_netmask": "255.255.255.0",
        "dhcp_scope_start": "192.168.0.2", "dhcp_scope_end": "192.168.0.254",
    }]
    spec = f.network_specs(nets, "matrix.lan", "192.168.0.1", "1.1.1.1")[0]

    assert spec["state"] == "active"
    assert spec["mode"] == "nat"
    assert spec["bridge_name"] == "virbr-vm"
    assert spec["autostart"] is True
    assert spec["domain"] == "matrix.lan"
    assert spec["dns"] == {"forwarders": ["192.168.0.1", "1.1.1.1"]}
    assert spec["dhcp"] == {
        "gateway": "192.168.0.1", "netmask": "255.255.255.0",
        "range_start": "192.168.0.2", "range_end": "192.168.0.254",
    }
    # the spec must be valid input for the module builder
    NetworkXMLBuilder(
        name=spec["name"], mode=spec["mode"], bridge_name=spec["bridge_name"],
        domain=spec["domain"], dns=spec["dns"], dhcp=spec["dhcp"],
    ).to_xml()


def test_network_specs_no_dhcp_omits_dhcp_dns():
    spec = f.network_specs([{"name": "iso", "mode": "private", "bridge_name": "br0"}])[0]
    assert "dhcp" not in spec
    assert "dns" not in spec
    assert "domain" not in spec


def test_network_specs_vlan_portgroups():
    nets = [{
        "name": "vl",
        "vlan": 42,
        "vlans": [
            {"name": "untagged", "default": True},
            {"name": "office", "vlan": 10},
            {"name": "trunk0", "trunk": True, "vlan": [10, 20, 30]},
        ],
    }]
    spec = f.network_specs(nets)[0]

    assert spec["vlan_tag"] == 42
    pgs = {pg["name"]: pg for pg in spec["vlans"]}
    assert pgs["untagged"] == {"name": "untagged", "trunk": False, "default": True, "tags": []}
    assert pgs["office"] == {"name": "office", "trunk": False, "tags": [10]}
    assert pgs["trunk0"] == {"name": "trunk0", "trunk": True, "tags": [10, 20, 30]}
    # valid for the builder
    NetworkXMLBuilder(name=spec["name"], vlan_tag=spec["vlan_tag"], vlans=spec["vlans"]).to_xml()


# -- instance_volumes ------------------------------------------------------

def test_instance_volumes():
    vm = {"name": "dns", "os": "debian", "os_disk_gb": 10,
          "data_disks": [{"name": "data0", "size_gb": 20}, {"name": "logs", "size_gb": 10}]}
    vols = f.instance_volumes(vm, {"debian": "debian-13.qcow2"})

    assert vols[0] == {"name": "dns-os.qcow2", "capacity": 10, "clone_source": "debian-13.qcow2"}
    assert vols[1] == {"name": "dns-data0.qcow2", "capacity": 20}
    assert vols[2] == {"name": "dns-logs.qcow2", "capacity": 10}
    for v in vols:
        VolumeXMLBuilder(name=v["name"], capacity=v["capacity"]).to_xml()


def test_instance_volumes_no_data_disks():
    vm = {"name": "x", "os": "arch", "os_disk_gb": 20, "data_disks": []}
    vols = f.instance_volumes(vm, {"arch": "arch.qcow2"})
    assert len(vols) == 1
    assert vols[0]["clone_source"] == "arch.qcow2"


# -- instance_disks --------------------------------------------------------

def test_instance_disks_layout():
    vm = {"name": "dns", "data_disks": [{"name": "data0", "size_gb": 20}, {"name": "logs", "size_gb": 10}]}
    disks = f.instance_disks(vm, "/pool", "virtio", "sata", ["b", "c", "d"])

    assert [d["target_dev"] for d in disks] == ["vda", "vdb", "vdc", "sda"]
    assert disks[0]["source"] == "/pool/dns-os.qcow2"
    assert disks[0]["bus"] == "virtio"
    assert disks[1]["source"] == "/pool/dns-data0.qcow2"
    assert disks[-1] == {"source": "/pool/dns-cidata.iso", "target_dev": "sda", "device": "cdrom", "bus": "sata"}

    DomainXMLBuilder(name=vm["name"], memory_mb=1024, vcpus=1, disks=disks,
                     interfaces=[{"source": "vm-network"}], graphics={"type": "none"}).to_xml()


def test_instance_disks_no_data_disks():
    disks = f.instance_disks({"name": "x", "data_disks": []}, "/pool")
    assert [d["target_dev"] for d in disks] == ["vda", "sda"]
