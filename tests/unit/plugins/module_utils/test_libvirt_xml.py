# -*- coding: utf-8 -*-

# (c) 2026, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the structured libvirt XML builders.

These run without libvirt-python and without a hypervisor; they only exercise
the pure parameter validation and XML rendering logic.
"""

from __future__ import absolute_import, division, print_function

import os
import sys
import xml.etree.ElementTree as ET

import pytest

# Allow importing the module_utils directly, without the full
# ansible_collections.bodsch.kvm import path.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "plugins", "module_utils"),
)

from libvirt_xml import (  # noqa: E402
    DomainXMLBuilder,
    NetworkXMLBuilder,
    PoolXMLBuilder,
    VolumeXMLBuilder,
    XMLValidationError,
    pool_target_path,
    to_bytes,
)


# -- to_bytes --------------------------------------------------------------

@pytest.mark.parametrize(
    "value,unit,expected",
    [
        (1, "B", 1),
        (1, "bytes", 1),
        (1, "K", 1024),
        (1, "KB", 1000),
        (1, "KiB", 1024),
        (10, "G", 10 * 1024 ** 3),
        (10, "GB", 10 * 1000 ** 3),
        (2, "TiB", 2 * 1024 ** 4),
    ],
)
def test_to_bytes(value, unit, expected):
    assert to_bytes(value, unit) == expected


def test_to_bytes_rejects_unknown_unit():
    with pytest.raises(XMLValidationError):
        to_bytes(1, "PB")


# -- VolumeXMLBuilder: rendering -------------------------------------------

def test_volume_xml_minimal():
    xml = VolumeXMLBuilder(name="disk.qcow2", capacity=20).to_xml()
    root = ET.fromstring(xml)

    assert root.tag == "volume"
    assert root.attrib["type"] == "file"
    assert root.find("name").text == "disk.qcow2"

    capacity = root.find("capacity")
    assert capacity.attrib["unit"] == "G"
    assert capacity.text == "20"

    assert root.find("target/format").attrib["type"] == "qcow2"
    # no allocation element unless requested
    assert root.find("allocation") is None


def test_volume_xml_with_allocation_and_format():
    xml = VolumeXMLBuilder(
        name="data.raw", capacity=5, unit="MiB", fmt="raw", allocation=1
    ).to_xml()
    root = ET.fromstring(xml)

    assert root.find("capacity").attrib["unit"] == "MiB"
    assert root.find("allocation").attrib["unit"] == "MiB"
    assert root.find("allocation").text == "1"
    assert root.find("target/format").attrib["type"] == "raw"


def test_capacity_bytes():
    builder = VolumeXMLBuilder(name="disk.qcow2", capacity=10, unit="G")
    assert builder.capacity_bytes() == 10 * 1024 ** 3


# -- VolumeXMLBuilder: validation ------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        dict(name="", capacity=10),
        dict(name="   ", capacity=10),
        dict(name="sub/disk.qcow2", capacity=10),       # path separator
        dict(name="disk.qcow2", capacity=0),            # non-positive
        dict(name="disk.qcow2", capacity=-1),
        dict(name="disk.qcow2", capacity=True),         # bool is not an int capacity
        dict(name="disk.qcow2", capacity=10, unit="PB"),
        dict(name="disk.qcow2", capacity=10, fmt="zfs"),
        dict(name="disk.qcow2", capacity=10, vol_type="weird"),
        dict(name="disk.qcow2", capacity=10, allocation=-5),
    ],
)
def test_volume_xml_rejects_invalid(kwargs):
    with pytest.raises(XMLValidationError):
        VolumeXMLBuilder(**kwargs)


# -- PoolXMLBuilder: rendering ---------------------------------------------

def test_pool_xml_minimal():
    xml = PoolXMLBuilder(name="default", target_path="/var/lib/libvirt/images").to_xml()
    root = ET.fromstring(xml)

    assert root.tag == "pool"
    assert root.attrib["type"] == "dir"
    assert root.find("name").text == "default"
    assert root.find("target/path").text == "/var/lib/libvirt/images"
    # no permissions / uuid unless requested
    assert root.find("target/permissions") is None
    assert root.find("uuid") is None


def test_pool_xml_with_permissions_and_uuid():
    xml = PoolXMLBuilder(
        name="data",
        target_path="/srv/pool",
        mode="0711",
        owner="107",
        group="107",
        uuid="a1b2c3d4-0000-0000-0000-000000000000",
    ).to_xml()
    root = ET.fromstring(xml)

    assert root.find("uuid").text == "a1b2c3d4-0000-0000-0000-000000000000"
    assert root.find("target/permissions/mode").text == "0711"
    assert root.find("target/permissions/owner").text == "107"
    assert root.find("target/permissions/group").text == "107"


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(name="", target_path="/srv/pool"),
        dict(name="a/b", target_path="/srv/pool"),          # path separator
        dict(name="data", target_path=""),                  # empty path
        dict(name="data", target_path="relative/path"),     # not absolute
        dict(name="data", target_path="/srv", pool_type="netfs"),   # unsupported type
        dict(name="data", target_path="/srv", mode="999"),  # not octal
        dict(name="data", target_path="/srv", mode="rwxr"),
        dict(name="data", target_path="/srv", owner="root"),  # not numeric
        dict(name="data", target_path="/srv", group="kvm"),
    ],
)
def test_pool_xml_rejects_invalid(kwargs):
    with pytest.raises(XMLValidationError):
        PoolXMLBuilder(**kwargs)


# -- pool_target_path ------------------------------------------------------

def test_pool_target_path_extracts():
    xml = """
    <pool type='dir'>
      <name>default</name>
      <target><path>/var/lib/libvirt/images</path></target>
    </pool>
    """
    assert pool_target_path(xml) == "/var/lib/libvirt/images"


def test_pool_target_path_missing_returns_none():
    xml = "<pool type='dir'><name>default</name><target/></pool>"
    assert pool_target_path(xml) is None


# -- NetworkXMLBuilder: rendering ------------------------------------------

def test_network_xml_nat_with_dhcp_dns_domain():
    xml = NetworkXMLBuilder(
        name="nat0",
        mode="nat",
        bridge_name="virbr10",
        domain="matrix.lan",
        dns={"forwarders": ["192.168.10.1", "1.1.1.1"]},
        dhcp={
            "gateway": "192.168.10.1",
            "netmask": "255.255.255.0",
            "range_start": "192.168.10.50",
            "range_end": "192.168.10.200",
        },
    ).to_xml()
    root = ET.fromstring(xml)

    assert root.find("name").text == "nat0"
    assert root.find("bridge").attrib["name"] == "virbr10"
    assert root.find("forward").attrib["mode"] == "nat"
    assert root.find("domain").attrib["name"] == "matrix.lan"
    assert [f.attrib["addr"] for f in root.findall("dns/forwarder")] == ["192.168.10.1", "1.1.1.1"]

    ip = root.find("ip")
    assert ip.attrib["address"] == "192.168.10.1"
    assert ip.attrib["netmask"] == "255.255.255.0"
    rng = root.find("ip/dhcp/range")
    assert rng.attrib["start"] == "192.168.10.50"
    assert rng.attrib["end"] == "192.168.10.200"


def test_network_xml_private_has_bridge_no_forward():
    xml = NetworkXMLBuilder(name="iso0", mode="private", bridge_name="virbr20").to_xml()
    root = ET.fromstring(xml)
    assert root.find("bridge").attrib["name"] == "virbr20"
    assert root.find("forward") is None


def test_network_xml_route_has_dev():
    xml = NetworkXMLBuilder(
        name="r0", mode="route", bridge_name="virbr30", route_device="eth0"
    ).to_xml()
    forward = ET.fromstring(xml).find("forward")
    assert forward.attrib["mode"] == "route"
    assert forward.attrib["dev"] == "eth0"


def test_network_xml_vlan_portgroups_and_network_tag():
    xml = NetworkXMLBuilder(
        name="vl",
        vlan_tag=42,
        vlans=[
            {"name": "untagged", "default": True, "trunk": False, "tags": []},
            {"name": "office", "trunk": False, "tags": [10]},
            {"name": "trunk0", "trunk": True, "tags": [10, 20, 30]},
        ],
    ).to_xml()
    root = ET.fromstring(xml)

    pgs = {pg.attrib["name"]: pg for pg in root.findall("portgroup")}
    assert pgs["untagged"].attrib.get("default") == "yes"
    assert pgs["untagged"].find("vlan") is None
    assert pgs["office"].find("vlan/tag").attrib["id"] == "10"
    assert pgs["trunk0"].find("vlan").attrib["trunk"] == "yes"
    assert [t.attrib["id"] for t in pgs["trunk0"].findall("vlan/tag")] == ["10", "20", "30"]

    # network-level vlan tag is rendered separately from portgroups
    net_vlans = [v for v in root.findall("vlan")]
    assert net_vlans and net_vlans[0].find("tag").attrib["id"] == "42"


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(name="", mode="nat", bridge_name="br0"),
        dict(name="a/b", mode="nat", bridge_name="br0"),
        dict(name="n", mode="weird", bridge_name="br0"),         # unknown mode
        dict(name="n", mode="nat"),                              # mode without bridge_name
        dict(name="n", mode="route", bridge_name="br0"),         # route without route_device
        dict(name="n", vlan_tag=4096),                           # tag out of range
        dict(name="n", vlan_tag=-1),
        dict(name="n", dhcp={"gateway": "192.168.0.1", "netmask": "255.255.255.0", "range_start": "192.168.0.10"}),  # missing range_end
        dict(name="n", dhcp={"gateway": "nope", "netmask": "255.255.255.0", "range_start": "192.168.0.10", "range_end": "192.168.0.20"}),  # bad ip
        dict(name="n", dhcp={"gateway": "192.168.0.1", "netmask": "999.0.0.0", "range_start": "192.168.0.10", "range_end": "192.168.0.20"}),  # bad netmask
        dict(name="n", dhcp={"gateway": "192.168.0.1", "netmask": "255.255.255.0", "range_start": "192.168.0.200", "range_end": "192.168.0.10"}),  # start > end
        dict(name="n", dns={"forwarders": ["1.1.1.1", "not-an-ip"]}),
        dict(name="n", vlans=[{"name": "a", "trunk": False, "tags": [1, 2]}]),   # non-trunk multiple tags
        dict(name="n", vlans=[{"name": "a", "trunk": True, "tags": []}]),        # trunk no tags
        dict(name="n", vlans=[{"name": "a", "tags": []}, {"name": "a", "tags": []}]),  # dup names
    ],
)
def test_network_xml_rejects_invalid(kwargs):
    with pytest.raises(XMLValidationError):
        NetworkXMLBuilder(**kwargs)


# -- DomainXMLBuilder: rendering -------------------------------------------

def test_domain_xml_basic():
    xml = DomainXMLBuilder(
        name="web01",
        memory_mb=2048,
        vcpus=2,
        disks=[
            {"source": "/img/web01-os.qcow2", "target_dev": "vda"},
            {"source": "/img/web01-cidata.iso", "target_dev": "sda", "device": "cdrom", "bus": "sata"},
        ],
        interfaces=[{"source": "bridge_network"}],
        graphics={"type": "spice"},
    ).to_xml()
    root = ET.fromstring(xml)

    assert root.attrib["type"] == "kvm"
    assert root.find("name").text == "web01"
    assert root.find("memory").attrib["unit"] == "MiB"
    assert root.find("memory").text == "2048"
    assert root.find("vcpu").text == "2"
    assert root.find("os/type").attrib["arch"] == "x86_64"
    assert root.find("os/type").text == "hvm"
    assert {f.tag for f in root.find("features")} == {"acpi", "apic"}

    disks = root.findall("devices/disk")
    assert disks[0].attrib == {"type": "file", "device": "disk"}
    assert disks[0].find("driver").attrib["type"] == "qcow2"
    assert disks[0].find("source").attrib["file"] == "/img/web01-os.qcow2"
    assert disks[0].find("target").attrib == {"dev": "vda", "bus": "virtio"}
    assert disks[0].find("readonly") is None

    # cdrom defaults to raw + readonly
    assert disks[1].attrib["device"] == "cdrom"
    assert disks[1].find("driver").attrib["type"] == "raw"
    assert disks[1].find("target").attrib["bus"] == "sata"
    assert disks[1].find("readonly") is not None

    iface = root.find("devices/interface")
    assert iface.attrib["type"] == "network"
    assert iface.find("source").attrib["network"] == "bridge_network"
    assert iface.find("model").attrib["type"] == "virtio"
    assert iface.find("mac") is None

    assert root.find("devices/graphics").attrib["type"] == "spice"
    assert root.find("devices/graphics").attrib["autoport"] == "yes"
    assert root.find("devices/console") is not None
    assert root.find("devices/rng").attrib["model"] == "virtio"


def test_domain_xml_headless_and_no_console_no_rng():
    xml = DomainXMLBuilder(
        name="head",
        memory_mb=1024,
        vcpus=1,
        graphics={"type": "none"},
        console=False,
        rng=False,
    ).to_xml()
    root = ET.fromstring(xml)
    assert root.find("devices/graphics") is None
    assert root.find("devices/console") is None
    assert root.find("devices/rng") is None


def test_domain_xml_bridge_interface_and_explicit_mac():
    xml = DomainXMLBuilder(
        name="b",
        memory_mb=512,
        vcpus=1,
        interfaces=[{"type": "bridge", "source": "br0", "mac": "52:54:00:ab:cd:ef"}],
    ).to_xml()
    iface = ET.fromstring(xml).find("devices/interface")
    assert iface.attrib["type"] == "bridge"
    assert iface.find("source").attrib["bridge"] == "br0"
    assert iface.find("mac").attrib["address"] == "52:54:00:ab:cd:ef"


def test_domain_xml_machine_and_uuid():
    xml = DomainXMLBuilder(
        name="m", memory_mb=512, vcpus=1, machine="q35",
        uuid="a1b2c3d4-0000-0000-0000-000000000000",
    ).to_xml()
    root = ET.fromstring(xml)
    assert root.find("os/type").attrib["machine"] == "q35"
    assert root.find("uuid").text == "a1b2c3d4-0000-0000-0000-000000000000"


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(name="", memory_mb=512, vcpus=1),
        dict(name="a/b", memory_mb=512, vcpus=1),
        dict(name="d", memory_mb=0, vcpus=1),
        dict(name="d", memory_mb=512, vcpus=0),
        dict(name="d", memory_mb=512, vcpus=1, domain_type="lxc"),
        dict(name="d", memory_mb=512, vcpus=1, features=["acpi", "hyperv"]),   # unsupported feature
        dict(name="d", memory_mb=512, vcpus=1, disks=[{"target_dev": "vda"}]),  # disk no source
        dict(name="d", memory_mb=512, vcpus=1, disks=[{"source": "/x"}]),       # disk no target_dev
        dict(name="d", memory_mb=512, vcpus=1, disks=[{"source": "/x", "target_dev": "vda", "bus": "weird"}]),
        dict(name="d", memory_mb=512, vcpus=1, disks=[{"source": "/x", "target_dev": "vda"}, {"source": "/y", "target_dev": "vda"}]),  # dup target
        dict(name="d", memory_mb=512, vcpus=1, interfaces=[{"model": "virtio"}]),  # iface no source
        dict(name="d", memory_mb=512, vcpus=1, interfaces=[{"source": "n", "type": "weird"}]),
        dict(name="d", memory_mb=512, vcpus=1, interfaces=[{"source": "n", "mac": "not-a-mac"}]),
        dict(name="d", memory_mb=512, vcpus=1, graphics={"type": "x11"}),       # bad graphics type
    ],
)
def test_domain_xml_rejects_invalid(kwargs):
    with pytest.raises(XMLValidationError):
        DomainXMLBuilder(**kwargs)
