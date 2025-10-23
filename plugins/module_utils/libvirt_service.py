
# -*- coding: utf-8 -*-

# (c) 2020-2023, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import, division, print_function

import os
import shutil

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.bodsch.systemd.plugins.module_utils.systemd import SystemdClient, SystemdError, UnitNotFoundError, AccessDeniedError, DBusIOError



class LibvirtService:
    """
    """
    def __init__(self, module):
        """
        """
        self.module = module
        self.module.log("LibvirtService::__init__()")


    def verify(self,
            user_manager: bool = False,
            services: list = [],
            service_types: list = ["service", "socket", "timer"],
            include_inactive: bool = True
        ):
        """
        """
        self.module.log(f"LibvirtService::verify(user_manager: {user_manager}, services: {services}, service_types: {service_types}, include_inactive: {include_inactive})")

        result_state = []

        service_matches = self.systemd_services(
            user_manager=user_manager,
            services=services,
            service_types=service_types,
            include_inactive=include_inactive
        )

        # self.module.log(f"name: {'Name':27} kind: {'Kind':7} state (active): {'state active':10} state (sub): {r.sub_state:8} masked: {r.is_masked} state: {(r.unit_file_state or '-'):10} {(r.load_state or '-'):10} {r.description}")
        for r in service_matches:
            self.module.log(f"name: {r.name:27} kind: {r.kind:7} state (active / sub): {r.active_state:8} / {r.sub_state:8} masked: {r.is_masked:7} state: {(r.unit_file_state or '-'):10}") # {(r.load_state or '-'):10} {r.description}")

        return service_matches

        # # {'libvirtd.service': {'enabled': 'enabled', 'active': 'inactive'}, 'libvirtd.socket': {'enabled': 'enabled', 'active': 'active'}}
        # mono_states  = {u.name: dict(enabled=u.unit_file_state, active=u.active_state) for u in service_matches if u.name in ["libvirtd.socket", "libvirtd.service"]}
        # # {'virtqemud.service': {'enabled': 'disabled', 'active': 'inactive'}, 'virtqemud.socket': {'enabled': 'disabled', 'active': 'inactive'}}
        # modu_states  = {u.name: dict(enabled=u.unit_file_state, active=u.active_state) for u in service_matches if u.name in ["virtqemud.socket", "virtqemud.service"]}
        #
        # monolithic = self.any_effectively_enabled(mono_states)
        # modular = self.any_effectively_enabled(modu_states)
        #
        # # self.module.log(f"{mono_states}")
        # # self.module.log(f"{modu_states}")
        #
        # # self.module.log(f"monolithic: {monolithic}")
        # # self.module.log(f"modulate  : {modular}")
        #
        # return dict(
        #     failed=False,
        #     changed=False,
        #     monolithic=monolithic,
        #     modular=modular
        # )
        #
        # #for r in results:
        # #    self.module.log(f"{r.name:40} {r.kind:7} {r.active_state:10} {r.sub_state:8} {(r.unit_file_state or '-'):10} {(r.load_state or '-'):10} {r.description}")
        #
        # return result_state

    def enable(self,
            user_manager: bool = False,
            services: list = [],
            service_types: list = ["service", "socket", "timer"],
            include_inactive: bool = True
        ):
        """
        """
        self.module.log(f"LibvirtService::enable(user_manager: {user_manager}, services: {services}, service_types: {service_types}, include_inactive: {include_inactive})")

        result_state = []
        service_matches = self.systemd_services(
            user_manager=user_manager,
            services=services,
            service_types=service_types,
            include_inactive=include_inactive
        )

        # {'libvirtd.service': {'enabled': 'enabled', 'active': 'inactive'}, 'libvirtd.socket': {'enabled': 'enabled', 'active': 'active'}}
        _states  = {u.name: dict(masked=u.is_masked, enabled=u.unit_file_state, active=u.active_state) for u in service_matches if u.name in self.units}

        # modular = self.any_effectively_enabled(_states)

        self.module.log(f"states : {_states}")
        # self.module.log(f"modular: {modular}")

        for srv, data in _states.items():
            self.module.log(f"- service: {srv} - {data}")
            res = {}

            if sd.exists(srv):
                _unmasked = False
                _enabled = False
                _changed = False

                unit_state = data.get("enabled", "enabled")
                active_state = data.get('active', 'active')
                active_masked = data.get('masked', True)

                self.module.log(f"   unit state   : '{unit_state}'")
                self.module.log(f"   active state : '{active_state}'")
                self.module.log(f"   active mask  : '{active_masked}'")

                if active_masked:
                    try:
                        _unmasked, _ = sd.unmask([srv])
                        self.module.log(f"unmask: {_unmasked}")
                        _changed = True

                    except UnitNotFoundError:
                        self.module.log("unknown")

                if not active_state == "active":
                    try:
                        _enabled, _ = sd.enable([srv])
                        self.module.log(f"activate: {_enabled}")
                        _changed = True

                    except UnitNotFoundError:
                        self.module.log("unknown")

                res[srv] = dict(
                    changed=_changed,
                    unmasked=_unmasked,
                    enabled=_enabled,
                )
            else:
                res[srv] = dict(
                    changed=False,
                    failed=True,
                    msg="service not exists."
                )

            result_state.append(res)

        return result_state


    def disable(self,
            user_manager: bool = False,
            services: list = [],
            service_types: list = ["service", "socket", "timer"],
            include_inactive: bool = True
        ):
        """
        """
        self.module.log(f"LibvirtService::disable(user_manager: {user_manager}, services: {services}, service_types: {service_types}, include_inactive: {include_inactive})")

        result_state = []
        service_matches = self.systemd_services(
            user_manager=user_manager,
            services=services,
            service_types=service_types,
            include_inactive=include_inactive
        )

        # {'libvirtd.service': {'enabled': 'enabled', 'active': 'inactive'}, 'libvirtd.socket': {'enabled': 'enabled', 'active': 'active'}}
        mono_states  = {u.name: dict(enabled=u.unit_file_state, active=u.active_state) for u in service_matches if u.name in self.units}

        monolithic = self.any_effectively_enabled(mono_states)

        self.module.log(f"{mono_states}")
        self.module.log(f"monolithic: {monolithic}")

        if monolithic:
            for srv, data in mono_states.items():
                self.module.log(f"- service: {srv} - {data}")

                if sd.exists(srv):
                    unit_state = data.get("enabled", "enabled")
                    active_state = data.get('active', 'active')
                    self.module.log(f"   unit state   : {unit_state}")
                    self.module.log(f"   active state : {active_state}")

                    service_file = sd.is_active(srv)
                    try:
                        service_state = sd.active_state(srv)
                    except UnitNotFoundError:
                        pass

                    self.module.log(f"   service file : {service_file}")
                    self.module.log(f"   service state: {service_state}")

                    if active_state == "active":
                        self.module.log("  stop")
                        try:
                            state = sd.stop(srv)
                            self.module.log(f"   state: {state}")
                        except UnitNotFoundError:
                            self.module.log("unknown")

                    if unit_state == "enabled":
                        self.module.log("  disable")
                        try:
                            state = sd.disable([srv])
                            self.module.log(f"   state: {state}")
                        except UnitNotFoundError:
                            self.module.log("unknown")

        return result_state

        return dict(
            failed=False,
            msg="all monolithic service stopped and disabled."
        )


    def start(self):
        """
        """
        pass

    def stop(self):
        """
        """
        pass

    def any_effectively_enabled(self, d: dict[str, dict[str, str]]) -> bool:

        enabled_states = {"enabled", "enabled-runtime", "linked", "linked-runtime", "alias"}

        return any((v.get("enabled") or "").lower() in enabled_states for v in d.values())

    def systemd_services(self,
            user_manager: bool = False,
            services: list = [],
            service_types: list = ["service", "socket", "timer"],
            include_inactive: bool = True
        ):
        """
        """
        self.module.log(f"LibvirtService::systemd_services(user_manager: {user_manager}, services: {services}, service_types: {service_types}, include_inactive: {include_inactive})")

        service_matches = []

        with SystemdClient(user_manager=user_manager) as sd:
            try:
                service_matches = sd.match_units(
                  patterns=services,
                  types=service_types,
                  include_inactive_files=include_inactive
                )
            except UnitNotFoundError:
                self.module.log("unknown")

        self.module.log(f"service_matches: {service_matches}")

        return service_matches

