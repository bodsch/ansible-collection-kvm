# -*- coding: utf-8 -*-

# (c) 2026, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

"""
Structured XML builders for the bodsch.kvm libvirt modules.

Each builder takes validated, structured parameters and produces the libvirt
XML that the freestyle ``xml:`` blocks of community.libvirt used to require.
Semantic validation lives here (and raises ``XMLValidationError``) so that an
invalid definition is rejected *before* it ever reaches the hypervisor.

The builders use the standard-library ``xml.etree.ElementTree`` only, so the
modules stay importable without any third-party XML dependency.
"""

from __future__ import absolute_import, division, print_function

import ipaddress
import re
import xml.etree.ElementTree as ET


class XMLValidationError(Exception):
    """Raised when structured parameters fail semantic validation."""

    pass


# libvirt accepts these values for the ``unit`` attribute of <capacity>/<allocation>.
# The factor is the number of bytes one unit represents.
#   * the "...B" forms are decimal (powers of 1000)
#   * the bare and "...iB" forms are binary (powers of 1024)
# See https://libvirt.org/format.html (storage volume "unit" attribute).
CAPACITY_UNITS = {
    "B": 1,
    "bytes": 1,
    "KB": 1000,
    "K": 1024,
    "KiB": 1024,
    "MB": 1000 ** 2,
    "M": 1024 ** 2,
    "MiB": 1024 ** 2,
    "GB": 1000 ** 3,
    "G": 1024 ** 3,
    "GiB": 1024 ** 3,
    "TB": 1000 ** 4,
    "T": 1024 ** 4,
    "TiB": 1024 ** 4,
}

# Storage volume target formats we accept. libvirt knows more, but this is the
# vetted subset relevant to this collection; extend deliberately.
VOLUME_FORMATS = {"raw", "qcow2", "qcow", "qed", "vmdk", "vdi", "vpc", "iso"}

# libvirt storage volume types.
VOLUME_TYPES = {"file", "block", "dir", "network", "netdir", "ploop"}


def to_bytes(value, unit):
    """Convert a (value, unit) capacity pair into an integer number of bytes."""
    if unit not in CAPACITY_UNITS:
        raise XMLValidationError(
            f"unknown capacity unit '{unit}'; expected one of {sorted(CAPACITY_UNITS)}"
        )
    return int(value) * CAPACITY_UNITS[unit]


class VolumeXMLBuilder:
    """
    Build and validate a libvirt storage ``<volume>`` definition.

    Replaces the freestyle XML previously passed to
    ``community.libvirt.virt_volume`` for ``command: create``.
    """

    def __init__(self, name, capacity, unit="G", fmt="qcow2", vol_type="file", allocation=None):
        """ """
        self.name = name
        self.capacity = capacity
        self.unit = unit
        self.fmt = fmt
        self.vol_type = vol_type
        self.allocation = allocation

        self._validate()

    def _validate(self):
        """Reject structurally or semantically invalid parameters."""
        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise XMLValidationError("volume 'name' must be a non-empty string")

        if "/" in self.name:
            raise XMLValidationError(
                f"volume name '{self.name}' must not contain a path separator '/'"
            )

        if not isinstance(self.capacity, int) or isinstance(self.capacity, bool):
            raise XMLValidationError("volume 'capacity' must be an integer")

        if self.capacity <= 0:
            raise XMLValidationError(
                f"volume 'capacity' must be greater than 0, got {self.capacity}"
            )

        if self.unit not in CAPACITY_UNITS:
            raise XMLValidationError(
                f"unknown capacity unit '{self.unit}'; expected one of {sorted(CAPACITY_UNITS)}"
            )

        if self.fmt not in VOLUME_FORMATS:
            raise XMLValidationError(
                f"unknown volume format '{self.fmt}'; expected one of {sorted(VOLUME_FORMATS)}"
            )

        if self.vol_type not in VOLUME_TYPES:
            raise XMLValidationError(
                f"unknown volume type '{self.vol_type}'; expected one of {sorted(VOLUME_TYPES)}"
            )

        if self.allocation is not None:
            if not isinstance(self.allocation, int) or isinstance(self.allocation, bool):
                raise XMLValidationError("volume 'allocation' must be an integer")
            if self.allocation < 0:
                raise XMLValidationError(
                    f"volume 'allocation' must not be negative, got {self.allocation}"
                )

    def capacity_bytes(self):
        """Return the requested capacity expressed in bytes (for resize comparison)."""
        return to_bytes(self.capacity, self.unit)

    def to_xml(self):
        """Render the validated definition into a libvirt XML string."""
        volume = ET.Element("volume", attrib={"type": self.vol_type})

        ET.SubElement(volume, "name").text = self.name

        capacity = ET.SubElement(volume, "capacity", attrib={"unit": self.unit})
        capacity.text = str(self.capacity)

        if self.allocation is not None:
            allocation = ET.SubElement(volume, "allocation", attrib={"unit": self.unit})
            allocation.text = str(self.allocation)

        target = ET.SubElement(volume, "target")
        ET.SubElement(target, "format", attrib={"type": self.fmt})

        return ET.tostring(volume, encoding="unicode")


# Storage pool types this collection can build. libvirt knows many more
# (fs, netfs, logical, disk, iscsi, rbd, ...) - extend deliberately, together
# with the matching <source>/<target> structure.
POOL_TYPES = {"dir"}

_MODE_RE = re.compile(r"^[0-7]{3,4}$")


def pool_target_path(xml_desc):
    """
    Extract ``/pool/target/path`` from a storage pool's XML description.

    Returns the path string, or ``None`` if the pool has no target path.
    Replaces the ``virt_pool command: get_xml`` + ``ansible.builtin.xml`` dance
    previously used by the roles to discover a pool's directory.
    """
    root = ET.fromstring(xml_desc)
    node = root.find("target/path")
    if node is None or node.text is None:
        return None
    return node.text.strip()


class PoolXMLBuilder:
    """
    Build and validate a libvirt storage ``<pool>`` definition.

    Replaces the freestyle XML / ``pool.xml.j2`` template previously passed to
    ``community.libvirt.virt_pool`` for ``command: define``. Currently models
    directory pools (C(type=dir)).
    """

    def __init__(self, name, target_path, pool_type="dir", mode=None, owner=None, group=None, uuid=None):
        """ """
        self.name = name
        self.target_path = target_path
        self.pool_type = pool_type
        self.mode = mode
        self.owner = owner
        self.group = group
        self.uuid = uuid

        self._validate()

    def _validate(self):
        """Reject structurally or semantically invalid parameters."""
        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise XMLValidationError("pool 'name' must be a non-empty string")

        if "/" in self.name:
            raise XMLValidationError(
                f"pool name '{self.name}' must not contain a path separator '/'"
            )

        if self.pool_type not in POOL_TYPES:
            raise XMLValidationError(
                f"unsupported pool type '{self.pool_type}'; supported: {sorted(POOL_TYPES)}"
            )

        if not self.target_path or not isinstance(self.target_path, str) or not self.target_path.strip():
            raise XMLValidationError("pool 'target_path' must be a non-empty string")

        if not self.target_path.startswith("/"):
            raise XMLValidationError(
                f"pool 'target_path' must be an absolute path, got '{self.target_path}'"
            )

        if self.mode is not None and not _MODE_RE.match(str(self.mode)):
            raise XMLValidationError(
                f"pool 'mode' must be an octal permission like '0755', got '{self.mode}'"
            )

        for key, value in (("owner", self.owner), ("group", self.group)):
            if value is not None and not str(value).isdigit():
                raise XMLValidationError(
                    f"pool '{key}' must be a numeric uid/gid, got '{value}'"
                )

    def to_xml(self):
        """Render the validated definition into a libvirt XML string."""
        pool = ET.Element("pool", attrib={"type": self.pool_type})

        ET.SubElement(pool, "name").text = self.name

        if self.uuid is not None:
            ET.SubElement(pool, "uuid").text = str(self.uuid)

        target = ET.SubElement(pool, "target")
        ET.SubElement(target, "path").text = self.target_path

        if self.mode is not None or self.owner is not None or self.group is not None:
            permissions = ET.SubElement(target, "permissions")
            if self.mode is not None:
                ET.SubElement(permissions, "mode").text = str(self.mode)
            if self.owner is not None:
                ET.SubElement(permissions, "owner").text = str(self.owner)
            if self.group is not None:
                ET.SubElement(permissions, "group").text = str(self.group)

        return ET.tostring(pool, encoding="unicode")


# Virtual network forward "modes" understood by this collection. C(private)
# is a libvirt-managed bridge without a forward element (an isolated network).
NETWORK_MODES = {"nat", "route", "bridge", "private"}

VLAN_TAG_MIN = 0
VLAN_TAG_MAX = 4095


def _is_ipv4(value):
    """Return True if ``value`` is a valid IPv4 address string."""
    try:
        ipaddress.IPv4Address(value)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


class NetworkXMLBuilder:
    """
    Build and validate a libvirt virtual ``<network>`` definition.

    Replaces the freestyle XML / ``network.xml.j2`` template previously passed
    to ``community.libvirt.virt_net`` for ``command: define``.
    """

    def __init__(self, name, mode=None, bridge_name=None, route_device=None,
                 virtualport_type=None, domain=None, dns=None, dhcp=None,
                 vlan_tag=None, vlans=None, uuid=None):
        """ """
        self.name = name
        self.mode = mode
        self.bridge_name = bridge_name
        self.route_device = route_device
        self.virtualport_type = virtualport_type
        self.domain = domain
        self.dns = dns or {}
        self.dhcp = dhcp or {}
        self.vlan_tag = vlan_tag
        self.vlans = vlans or []
        self.uuid = uuid

        self._validate()

    def _validate(self):
        """Reject structurally or semantically invalid parameters."""
        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise XMLValidationError("network 'name' must be a non-empty string")

        if "/" in self.name:
            raise XMLValidationError(
                f"network name '{self.name}' must not contain a path separator '/'"
            )

        if self.mode is not None and self.mode not in NETWORK_MODES:
            raise XMLValidationError(
                f"unknown network mode '{self.mode}'; expected one of {sorted(NETWORK_MODES)}"
            )

        if self.mode in NETWORK_MODES and not self.bridge_name:
            raise XMLValidationError(
                f"network mode '{self.mode}' requires 'bridge_name'"
            )

        if self.mode == "route" and not self.route_device:
            raise XMLValidationError("network mode 'route' requires 'route_device'")

        self._validate_dhcp()
        self._validate_dns()

        if self.vlan_tag is not None:
            self._validate_tag(self.vlan_tag, "vlan_tag")

        self._validate_vlans()

    def _validate_dhcp(self):
        """ """
        if not self.dhcp:
            return

        for key in ("gateway", "netmask", "range_start", "range_end"):
            if not self.dhcp.get(key):
                raise XMLValidationError(f"dhcp '{key}' is required when 'dhcp' is given")

        for key in ("gateway", "range_start", "range_end"):
            if not _is_ipv4(self.dhcp[key]):
                raise XMLValidationError(
                    f"dhcp '{key}' must be a valid IPv4 address, got '{self.dhcp[key]}'"
                )

        try:
            ipaddress.IPv4Network(f"{self.dhcp['gateway']}/{self.dhcp['netmask']}", strict=False)
        except (ipaddress.NetmaskValueError, ipaddress.AddressValueError, ValueError):
            raise XMLValidationError(f"dhcp 'netmask' '{self.dhcp['netmask']}' is not a valid netmask")

        if int(ipaddress.IPv4Address(self.dhcp["range_start"])) > int(ipaddress.IPv4Address(self.dhcp["range_end"])):
            raise XMLValidationError("dhcp 'range_start' must not be greater than 'range_end'")

    def _validate_dns(self):
        """ """
        for forwarder in self.dns.get("forwarders", []):
            if not _is_ipv4(forwarder):
                raise XMLValidationError(
                    f"dns forwarder must be a valid IPv4 address, got '{forwarder}'"
                )

    def _validate_tag(self, tag, field):
        """ """
        if not isinstance(tag, int) or isinstance(tag, bool) or not (VLAN_TAG_MIN <= tag <= VLAN_TAG_MAX):
            raise XMLValidationError(
                f"{field} must be an integer {VLAN_TAG_MIN}-{VLAN_TAG_MAX}, got {tag!r}"
            )

    def _validate_vlans(self):
        """ """
        seen = set()
        for pg in self.vlans:
            name = pg.get("name")
            if not name:
                raise XMLValidationError("each vlan portgroup requires a 'name'")
            if name in seen:
                raise XMLValidationError(f"duplicate vlan portgroup name '{name}'")
            seen.add(name)

            tags = pg.get("tags") or []
            for tag in tags:
                self._validate_tag(tag, f"portgroup '{name}' tag")

            if pg.get("trunk"):
                if len(tags) < 1:
                    raise XMLValidationError(f"trunk portgroup '{name}' requires at least one tag")
            elif len(tags) > 1:
                raise XMLValidationError(
                    f"non-trunk portgroup '{name}' may have at most one vlan tag"
                )

    def to_xml(self):
        """Render the validated definition into a libvirt XML string."""
        net = ET.Element("network")
        ET.SubElement(net, "name").text = self.name

        if self.uuid is not None:
            ET.SubElement(net, "uuid").text = str(self.uuid)

        if self.mode in NETWORK_MODES:
            ET.SubElement(net, "bridge", attrib={"name": self.bridge_name})
            if self.mode == "nat":
                ET.SubElement(net, "forward", attrib={"mode": "nat"})
            elif self.mode == "bridge":
                ET.SubElement(net, "forward", attrib={"mode": "bridge"})
            elif self.mode == "route":
                ET.SubElement(net, "forward", attrib={"mode": "route", "dev": self.route_device})
            # 'private' -> bridge only, no forward (isolated network)

        if self.virtualport_type:
            ET.SubElement(net, "virtualport", attrib={"type": self.virtualport_type})

        if self.domain:
            ET.SubElement(net, "domain", attrib={"name": self.domain})

        forwarders = self.dns.get("forwarders", [])
        if forwarders:
            dns = ET.SubElement(net, "dns")
            for forwarder in forwarders:
                ET.SubElement(dns, "forwarder", attrib={"addr": forwarder})

        if self.dhcp:
            ip = ET.SubElement(
                net, "ip",
                attrib={"address": self.dhcp["gateway"], "netmask": self.dhcp["netmask"]},
            )
            dhcp = ET.SubElement(ip, "dhcp")
            ET.SubElement(
                dhcp, "range",
                attrib={"start": self.dhcp["range_start"], "end": self.dhcp["range_end"]},
            )

        for pg in self.vlans:
            attrib = {"name": pg["name"]}
            if pg.get("default"):
                attrib["default"] = "yes"
            portgroup = ET.SubElement(net, "portgroup", attrib=attrib)

            tags = pg.get("tags") or []
            if tags:
                if pg.get("trunk"):
                    vlan = ET.SubElement(portgroup, "vlan", attrib={"trunk": "yes"})
                    for tag in tags:
                        ET.SubElement(vlan, "tag", attrib={"id": str(tag)})
                else:
                    vlan = ET.SubElement(portgroup, "vlan")
                    ET.SubElement(vlan, "tag", attrib={"id": str(tags[0])})

        if self.vlan_tag is not None:
            vlan = ET.SubElement(net, "vlan")
            ET.SubElement(vlan, "tag", attrib={"id": str(self.vlan_tag)})

        return ET.tostring(net, encoding="unicode")


# Vetted subsets for the domain builder. Extend deliberately.
DOMAIN_TYPES = {"kvm", "qemu"}
SIMPLE_FEATURES = {"acpi", "apic", "pae"}
DISK_DEVICES = {"disk", "cdrom"}
DISK_BUSES = {"virtio", "sata", "ide", "scsi", "usb"}
INTERFACE_TYPES = {"network", "bridge"}
GRAPHICS_TYPES = {"vnc", "spice", "none"}

# libvirt domain state id -> human readable name (virDomainState).
DOMAIN_STATE_NAMES = {
    0: "nostate",
    1: "running",
    2: "blocked",
    3: "paused",
    4: "shutdown",
    5: "shutoff",
    6: "crashed",
    7: "pmsuspended",
}

# the source attribute name carrying the "network" of an interface, per type
INTERFACE_SOURCE_ATTR = {"network": "network", "bridge": "bridge"}

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


class DomainXMLBuilder:
    """
    Build and validate a libvirt ``<domain>`` definition from a structured
    subset of parameters.

    Replaces the freestyle XML / ``vm.xml.j2`` template previously passed to
    ``community.libvirt.virt`` for ``command: define``. Covers the common case
    (memory, vcpus, file disks, network interfaces, graphics, console, rng);
    exotic configurations are handled by the module's ``raw_xml`` escape hatch
    instead of this builder.
    """

    def __init__(self, name, memory_mb, vcpus, disks=None, interfaces=None,
                 domain_type="kvm", arch="x86_64", machine=None, features=None,
                 graphics=None, console=True, rng=True, uuid=None):
        """ """
        self.name = name
        self.memory_mb = memory_mb
        self.vcpus = vcpus
        self.disks = disks or []
        self.interfaces = interfaces or []
        self.domain_type = domain_type
        self.arch = arch
        self.machine = machine
        self.features = ["acpi", "apic"] if features is None else features
        self.graphics = graphics
        self.console = console
        self.rng = rng
        self.uuid = uuid

        self._validate()

    def _validate(self):
        """Reject structurally or semantically invalid parameters."""
        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise XMLValidationError("domain 'name' must be a non-empty string")

        if "/" in self.name:
            raise XMLValidationError(
                f"domain name '{self.name}' must not contain a path separator '/'"
            )

        if self.domain_type not in DOMAIN_TYPES:
            raise XMLValidationError(
                f"unknown domain type '{self.domain_type}'; expected one of {sorted(DOMAIN_TYPES)}"
            )

        for field, value in (("memory_mb", self.memory_mb), ("vcpus", self.vcpus)):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise XMLValidationError(f"domain '{field}' must be an integer greater than 0")

        if not self.arch:
            raise XMLValidationError("domain 'arch' must be a non-empty string")

        for feature in self.features:
            if feature not in SIMPLE_FEATURES:
                raise XMLValidationError(
                    f"unsupported feature '{feature}'; supported toggles: {sorted(SIMPLE_FEATURES)}"
                )

        self._validate_disks()
        self._validate_interfaces()
        self._validate_graphics()

    def _validate_disks(self):
        """ """
        seen_targets = set()
        for disk in self.disks:
            if not disk.get("source"):
                raise XMLValidationError("each disk requires a 'source'")
            target_dev = disk.get("target_dev")
            if not target_dev:
                raise XMLValidationError("each disk requires a 'target_dev'")
            if target_dev in seen_targets:
                raise XMLValidationError(f"duplicate disk target_dev '{target_dev}'")
            seen_targets.add(target_dev)

            device = disk.get("device") or "disk"
            if device not in DISK_DEVICES:
                raise XMLValidationError(
                    f"unknown disk device '{device}'; expected one of {sorted(DISK_DEVICES)}"
                )

            bus = disk.get("bus") or "virtio"
            if bus not in DISK_BUSES:
                raise XMLValidationError(
                    f"unknown disk bus '{bus}'; expected one of {sorted(DISK_BUSES)}"
                )

    def _validate_interfaces(self):
        """ """
        for iface in self.interfaces:
            iface_type = iface.get("type") or "network"
            if iface_type not in INTERFACE_TYPES:
                raise XMLValidationError(
                    f"unknown interface type '{iface_type}'; expected one of {sorted(INTERFACE_TYPES)}"
                )
            if not iface.get("source"):
                raise XMLValidationError("each interface requires a 'source'")
            mac = iface.get("mac")
            if mac is not None and not _MAC_RE.match(mac):
                raise XMLValidationError(f"interface 'mac' '{mac}' is not a valid MAC address")

    def _validate_graphics(self):
        """ """
        if not self.graphics:
            return
        gtype = self.graphics.get("type")
        if gtype not in GRAPHICS_TYPES:
            raise XMLValidationError(
                f"unknown graphics type '{gtype}'; expected one of {sorted(GRAPHICS_TYPES)}"
            )

    def to_xml(self):
        """Render the validated definition into a libvirt XML string."""
        domain = ET.Element("domain", attrib={"type": self.domain_type})

        ET.SubElement(domain, "name").text = self.name
        if self.uuid is not None:
            ET.SubElement(domain, "uuid").text = str(self.uuid)

        ET.SubElement(domain, "memory", attrib={"unit": "MiB"}).text = str(self.memory_mb)
        ET.SubElement(domain, "vcpu").text = str(self.vcpus)

        os_el = ET.SubElement(domain, "os")
        type_attrib = {"arch": self.arch}
        if self.machine:
            type_attrib["machine"] = self.machine
        ET.SubElement(os_el, "type", attrib=type_attrib).text = "hvm"

        if self.features:
            features_el = ET.SubElement(domain, "features")
            for feature in self.features:
                ET.SubElement(features_el, feature)

        devices = ET.SubElement(domain, "devices")

        for disk in self.disks:
            self._render_disk(devices, disk)

        for iface in self.interfaces:
            self._render_interface(devices, iface)

        if self.console:
            console = ET.SubElement(devices, "console", attrib={"type": "pty"})
            ET.SubElement(console, "target", attrib={"type": "virtio", "port": "1"})

        if self.graphics and self.graphics.get("type") not in (None, "none"):
            self._render_graphics(devices, self.graphics)

        if self.rng:
            rng = ET.SubElement(devices, "rng", attrib={"model": "virtio"})
            ET.SubElement(rng, "backend", attrib={"model": "random"}).text = "/dev/urandom"

        return ET.tostring(domain, encoding="unicode")

    def _render_disk(self, devices, disk):
        """ """
        device = disk.get("device") or "disk"
        fmt = disk.get("format") or ("raw" if device == "cdrom" else "qcow2")
        bus = disk.get("bus") or "virtio"
        readonly = disk.get("readonly")
        if readonly is None:
            readonly = device == "cdrom"

        disk_el = ET.SubElement(devices, "disk", attrib={"type": "file", "device": device})
        ET.SubElement(disk_el, "driver", attrib={"name": "qemu", "type": fmt})
        ET.SubElement(disk_el, "source", attrib={"file": disk["source"]})
        ET.SubElement(disk_el, "target", attrib={"dev": disk["target_dev"], "bus": bus})
        if readonly:
            ET.SubElement(disk_el, "readonly")

    def _render_interface(self, devices, iface):
        """ """
        iface_type = iface.get("type") or "network"
        model = iface.get("model") or "virtio"

        iface_el = ET.SubElement(devices, "interface", attrib={"type": iface_type})
        if iface.get("mac"):
            ET.SubElement(iface_el, "mac", attrib={"address": iface["mac"]})
        ET.SubElement(iface_el, "source", attrib={INTERFACE_SOURCE_ATTR[iface_type]: iface["source"]})
        ET.SubElement(iface_el, "model", attrib={"type": model})

    def _render_graphics(self, devices, graphics):
        """ """
        attrib = {"type": graphics["type"]}
        attrib["autoport"] = "yes" if graphics.get("autoport", True) else "no"
        if graphics.get("listen"):
            attrib["listen"] = graphics["listen"]
        ET.SubElement(devices, "graphics", attrib=attrib)
