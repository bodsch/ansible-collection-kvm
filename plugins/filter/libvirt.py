# python 3 headers, required if submitting to Ansible

from __future__ import absolute_import, print_function

__metaclass__ = type

from ansible.utils.display import Display

display = Display()


class FilterModule(object):
    """
    Ansible file jinja2 tests
    """

    def filters(self):
        return {
            "security_drivers": self.security_drivers,
            "cgroup_controllers": self.cgroup_controllers,
            "modular_daemons": self.modular_daemons,
            "modular_daemons_off": self.modular_daemons_off,
            "libvirt_proxy_daemons": self.libvirt_proxy_daemons,
            "network_specs": self.network_specs,
            "instance_volumes": self.instance_volumes,
            "instance_disks": self.instance_disks,
        }

    def instance_volumes(self, vm, os_base_volumes):
        """
        Volume specs for bodsch.kvm.libvirt_volume: the cloned OS disk plus one
        empty data disk per entry in C(vm.data_disks).
        """
        display.v(f"instance_volumes({vm}, {os_base_volumes})")

        volumes = [{
            "name": f"{vm['name']}-os.qcow2",
            "capacity": vm["os_disk_gb"],
            "clone_source": os_base_volumes[vm["os"]],
        }]

        for disk in vm.get("data_disks", []):
            volumes.append({
                "name": f"{vm['name']}-{disk['name']}.qcow2",
                "capacity": disk["size_gb"],
            })

        return volumes

    def instance_disks(self, vm, pool_path, root_disk_bus="virtio",
                       cdrom_bus="sata", data_disk_letters=None):
        """
        Disk device specs for bodsch.kvm.libvirt_domain: OS disk on C(vda), one
        data disk per C(vm.data_disks) (vdb, vdc, ...), and the cloud-init seed
        ISO as a read-only cdrom. Mirrors the former vm.xml.j2 device layout.
        """
        display.v(f"instance_disks({vm}, {pool_path})")

        letters = data_disk_letters or ["b", "c", "d", "e", "f", "g", "h", "i"]

        disks = [{
            "source": f"{pool_path}/{vm['name']}-os.qcow2",
            "target_dev": "vda",
            "bus": root_disk_bus,
        }]

        for index, disk in enumerate(vm.get("data_disks", [])):
            disks.append({
                "source": f"{pool_path}/{vm['name']}-{disk['name']}.qcow2",
                "target_dev": f"vd{letters[index]}",
                "bus": "virtio",
            })

        disks.append({
            "source": f"{pool_path}/{vm['name']}-cidata.iso",
            "target_dev": "sda",
            "device": "cdrom",
            "bus": cdrom_bus,
        })

        return disks

    def network_specs(self, networks, domain=None, dns_primary=None, dns_secondary=None):
        """
        Translate the role's flat ``virtual_networks`` items into the nested
        parameter schema of the bodsch.kvm.libvirt_network module.

        The role keeps its existing public data model (flat C(enable_dhcp) /
        C(dhcp_*) keys plus the role-level domain / DNS variables); this filter
        bridges it to the module's structured C(dns) / C(dhcp) sub-dicts and the
        C(vlan_tag) / C(vlans) (with C(tags)) shape.
        """
        display.v(f"network_specs({networks}, {domain}, {dns_primary}, {dns_secondary})")

        passthrough = ("state", "mode", "bridge_name", "route_device",
                       "virtualport_type", "uuid", "autostart")

        result = []

        for net in networks:
            spec = {"name": net["name"]}

            for key in passthrough:
                if key in net:
                    spec[key] = net[key]

            if net.get("enable_dhcp"):
                spec["dhcp"] = {
                    "gateway": net.get("dhcp_gateway"),
                    "netmask": net.get("dhcp_netmask"),
                    "range_start": net.get("dhcp_scope_start"),
                    "range_end": net.get("dhcp_scope_end"),
                }
                if domain:
                    spec["domain"] = domain
                forwarders = [a for a in (dns_primary, dns_secondary) if a]
                if forwarders:
                    spec["dns"] = {"forwarders": forwarders}

            if "vlan" in net:
                spec["vlan_tag"] = net["vlan"]

            if "vlans" in net:
                spec["vlans"] = [self._vlan_portgroup(vl) for vl in net["vlans"]]

            result.append(spec)

        display.v(f"= result: {result}")

        return result

    def _vlan_portgroup(self, vl):
        """
        Map a role VLAN portgroup ({name, default, trunk, vlan}) to the module's
        ({name, default, trunk, tags}) shape. For a non-trunk portgroup C(vlan)
        is a single id; for a trunk it is a list of ids; a default portgroup may
        omit C(vlan) entirely.
        """
        pg = {"name": vl["name"], "trunk": bool(vl.get("trunk", False))}

        if vl.get("default"):
            pg["default"] = True

        raw = vl.get("vlan")
        if raw is None:
            pg["tags"] = []
        elif pg["trunk"]:
            pg["tags"] = list(raw)
        else:
            pg["tags"] = [raw]

        return pg

    def security_drivers(self, data, default=["selinux", "apparmor"]):
        """ """
        display.v(f"security_drivers({data}, {default}")

        result = False

        if isinstance(data, list):
            for d in data:
                if d in default:
                    result = True

        display.v(f"= {result}")

        return result

    def cgroup_controllers(self, data):
        """ """
        display.v(f"security_drivers({data}")

        default = ["cpu", "devices", "memory", "blkio", "cpuset", "cpuacct"]
        result = []

        if isinstance(data, list):
            for d in data:
                if d in default:
                    result.append(d)

        display.v(f"= {result}")

        return result

    def modular_daemons(self, data, only_sockets=False, only_services=False):
        """
        The following modular daemons currently exist for hypervisor drivers

            - virtqemud  - the QEMU management daemon, for running virtual machines on UNIX platforms, optionally with KVM acceleration,
                           in either system or session mode
            - virtxend   - the Xen management daemon, for running virtual machines on the Xen hypervisor, in system mode only
            - virtlxcd   - the Linux Container management daemon, for running LXC guests in system mode only
            - virtbhyved - the BHyve management daemon, for running virtual machines on FreeBSD with the BHyve hypervisor, in system mode.
            - virtvboxd  - the VirtualBox management daemon, for running virtual machines on UNIX platforms.

        The additional modular daemons service secondary drivers

            - virtinterfaced - the host NIC management daemon, in system mode only
            - virtnetworkd - the virtual network management daemon, in system mode only
            - virtnodedevd - the host physical device management daemon, in system mode only
            - virtnwfilterd - the host firewall management daemon, in system mode only
            - virtsecretd - the host secret management daemon, in system or session mode
            - virtstoraged - the host storage management daemon, in system or session mode
        """
        display.v(
            f"modular_daemons({data}, only_sockets: {only_sockets}, only_services: {only_services})"
        )

        # The monolithic 'libvirtd' shares the same libvirt_services dict but is
        # never a modular virt*d daemon; drop it before generating unit names.
        data = {k: v for k, v in data.items() if k != "libvirtd"}

        result = []

        enabled_sockets = []
        enabled_services = []

        if only_sockets:
            sockets = {
                k: {ik: iv for ik, iv in v.items() if ik != "service"}
                for k, v in data.items()
            }
            enabled_sockets = self.only_enabled(sockets)
            enabled_sockets = list(enabled_sockets.keys())

            for x in enabled_sockets:
                result += self.modular_socket_units(x)

        if only_services:
            services = {
                k: {ik: iv for ik, iv in v.items() if ik != "socket"}
                for k, v in data.items()
            }
            enabled_services = self.only_enabled(services)
            enabled_services = list(enabled_services.keys())

            services = [f"virt{x}d.service" for x in enabled_services]
            result += services

        display.v(f"= result: {result}")

        return result

    def modular_socket_units(self, daemon, no_ro_socket=("lock", "log")):
        """
        Return the systemd socket units for a single modular daemon.

        Every daemon provides a primary 'virt<daemon>d.socket' and an
        '-admin.socket'. All daemons except virtlockd/virtlogd additionally
        provide a read-only '-ro.socket'. The proxy daemon's -tcp/-tls sockets
        are configuration-dependent and handled by libvirt_proxy_daemons().
        """
        units = [f"virt{daemon}d.socket"]
        if daemon not in no_ro_socket:
            units.append(f"virt{daemon}d-ro.socket")
        units.append(f"virt{daemon}d-admin.socket")

        return units

    def modular_daemons_off(self, data, keep=("libvirtd", "lock", "log")):
        """
        Service + socket units for every modular driver daemon present in
        libvirt_services, *regardless* of its enabled flag.

        Excludes the monolithic 'libvirtd' and the always-on virtlogd/virtlockd
        (both are shared with the monolithic libvirtd and must keep running).
        Used to disable the modular daemons when forcing the monolithic model.
        """
        display.v(f"modular_daemons_off({data}, keep: {keep})")

        units = []

        for daemon in data.keys():
            if daemon in keep:
                continue

            units.append(f"virt{daemon}d.service")
            units += self.modular_socket_units(daemon)

            if daemon == "proxy":
                units += ["virtproxyd-tcp.socket", "virtproxyd-tls.socket"]

        display.v(f"= result: {units}")

        return units

    def libvirt_proxy_daemons(
        self, data, config={}, only_sockets=False, only_services=False
    ):
        """..."""
        display.v(
            f"libvirt_proxy_daemons({data}, {config}, only_sockets: {only_sockets}, only_services: {only_services})"
        )

        daemons = []

        services = ["virtproxyd.service"]
        sockets = ["virtproxyd-ro.socket", "virtproxyd-admin.socket"]

        enabled_tls = config.get("listen_tls", False)
        enabled_tcp = config.get("listen_tcp", False)

        if enabled_tls:
            sockets += ["virtproxyd-tls.socket"]

        if enabled_tcp:
            sockets += ["virtproxyd-tcp.socket"]

        display.v(f" - {services}")
        display.v(f" - {sockets}")

        if only_services:
            daemons = services
        elif only_sockets:
            daemons = sockets
        else:
            daemons = services
            daemons += sockets

        display.v(f" - {daemons}")

        return daemons

    def only_enabled(self, d: dict) -> dict:
        """
        Filtert pro Top-Level-Key nur die Untermappings (z.B. 'socket'),
        deren 'enabled' True ist. Entfernt Top-Level-Keys ohne Treffer.
        """
        display.v(f"only_enabled({d})")

        result = {
            k: {
                ik: iv
                for ik, iv in v.items()
                if isinstance(iv, dict) and iv.get("enabled") is True
            }
            for k, v in d.items()
            if any(
                isinstance(iv, dict) and iv.get("enabled") is True for iv in v.values()
            )
        }

        display.v(f"= result {result}")

        return result
