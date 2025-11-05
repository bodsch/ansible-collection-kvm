# python 3 headers, required if submitting to Ansible

from __future__ import (absolute_import, print_function)

__metaclass__ = type

from ansible.utils.display import Display

display = Display()


class FilterModule(object):
    """
        Ansible file jinja2 tests
    """

    def filters(self):
        return {
            'combine_monolithic': self.combine_for_monolithic,
            'security_drivers': self.security_drivers,
            'cgroup_controllers': self.cgroup_controllers,
            'modular_daemons': self.modular_daemons,
            'libvirt_proxy_daemons': self.libvirt_proxy_daemons,
        }

    def combine_for_monolithic(self, data, config):
        """
        """
        display.v(f"combine_for_monolithic({data}, {config}")



        return {}


    def security_drivers(self, data, default=["selinux", "apparmor"]):
        """
        """
        display.v(f"security_drivers({data}, {default}")

        result = False

        if isinstance(data, list):
            for d in data:
                if d in default:
                    result = True

        display.v(f"= {result}")

        return result

    def cgroup_controllers(self, data):
        """
        """
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

                - virtqemud - the QEMU management daemon, for running virtual machines on UNIX platforms, optionally with KVM acceleration, in either system or session mode
                - virtxend - the Xen management daemon, for running virtual machines on the Xen hypervisor, in system mode only
                - virtlxcd - the Linux Container management daemon, for running LXC guests in system mode only
                - virtbhyved - the BHyve management daemon, for running virtual machines on FreeBSD with the BHyve hypervisor, in system mode.
                - virtvboxd - the VirtualBox management daemon, for running virtual machines on UNIX platforms.

            The additional modular daemons service secondary drivers

                - virtinterfaced - the host NIC management daemon, in system mode only
                - virtnetworkd - the virtual network management daemon, in system mode only
                - virtnodedevd - the host physical device management daemon, in system mode only
                - virtnwfilterd - the host firewall management daemon, in system mode only
                - virtsecretd - the host secret management daemon, in system or session mode
                - virtstoraged - the host storage management daemon, in system or session mode
        """
        display.v(f"modular_daemons({data}, only_sockets: {only_sockets}, only_services: {only_services})")

        result = []

        enabled_sockets = []
        enabled_services = []

        if only_sockets:
            sockets = {k: {ik: iv for ik, iv in v.items() if ik != 'service'} for k, v in data.items()}
            enabled_sockets = self.only_enabled(sockets)
            enabled_sockets = list(enabled_sockets.keys())

            sockets  = [f"virt{x}d-ro.socket"     for x in enabled_sockets]
            sockets += [f"virt{x}d-admin.socket"  for x in enabled_sockets]
            result += sockets

        if only_services:
            services = {k: {ik: iv for ik, iv in v.items() if ik != 'sockets'} for k, v in data.items()}
            enabled_services = self.only_enabled(services)
            enabled_services = list(enabled_services.keys())

            services = [f"virt{x}d.service"       for x in enabled_services]
            result += services

        display.v(f"= result: {result}")

        return result

    def libvirt_proxy_daemons(self, data, config={}, only_sockets=False, only_services=False):
        """ ... """
        display.v(f"libvirt_proxy_daemons({data}, {config}, only_sockets: {only_sockets}, only_services: {only_services})")

        daemons = []

        services = ["virtproxyd.service"]
        sockets = [
            "virtproxyd-ro.socket",
            "virtproxyd-admin.socket"
        ]

        enabled_tls = config.get('listen_tls', False)
        enabled_tcp = config.get('listen_tcp', False)

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
            k: {ik: iv for ik, iv in v.items()
                if isinstance(iv, dict) and iv.get('enabled') is True}
            for k, v in d.items()
            if any(isinstance(iv, dict) and iv.get('enabled') is True for iv in v.values())
        }

        display.v(f"= result {result}")

        return result
