#!/usr/bin/python3
# -*- coding: utf-8 -*-

# (c) 2020-2023, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import, division, print_function

import os
import shutil

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.bodsch.kvm.plugins.module_utils.libvirt_service import LibvirtService

from ansible_collections.bodsch.systemd.plugins.module_utils.systemd import SystemdClient, SystemdError, UnitNotFoundError, AccessDeniedError, DBusIOError
from ansible_collections.bodsch.core.plugins.module_utils.module_results import results


class LibvirtMonolitic(LibvirtService):
    """
    """
    module = None

    def __init__(self, module):
        """
        """
        self.module = module

        self.state = module.params.get("state")
        self.units = module.params.get("units")

        self.monolithic=["libvirtd.service","libvirtd.socket","libvirtd-ro.socket","libvirtd-admin.socket","libvirtd-tcp.socket","libvirtd-tls.socket"]

        super().__init__(module)

    def run(self):
        """
        """
        result = dict(
            rc=1,
            failed=True,
            changed=False,
        )

        result_status = []
        result_state = {}

        _verifyed_services = self.__verify_services()

        _monolithic_services = {u.name: dict(enabled=u.unit_file_state, active=u.active_state) for u in _verifyed_services if u.name in self.monolithic}

        self.module.log(f" - monolithic services: {_monolithic_services}")

        if self.state == "disable":
            _active_services = [x for x,v in _monolithic_services.items() if v.get('enabled', "disabled") == "enabled" and v.get("active", "active") == "active"]
            self.module.log(f" - active monolithic services: {_active_services}")

            result_state = self.__disable_services(services=_active_services)

        # if self.state == "verify":
        #     return self.__verify_services()
        #
        # if self.state == "disable":
        #     result_state = self.__disable_services()
        #
        # if self.state == "enable":
        #     result_state = self.__enable_services()
        #
        # if self.state == "start":
        #     result_state = self.__start_services()

        try:
            _state, _changed, _failed, state, changed, failed = results(self.module, result_state)

            result = dict(
                changed=_changed,
                failed=False,
                state=result_state
            )
            return result

        except Exception as e:
            self.module.log(f"error: {e}")
            return result_state


    def __verify_services(self):
        """ ... """
        self.module.log("LibvirtMonolitic::__verify_services()")

        _verified = self.verify(
            user_manager=False,
            services=self.units,
            service_types=["service", "socket", "timer"],
            include_inactive=True
        )

        self.module.log(f"_verified: {_verified}")

        return _verified

        result_state = []

        with SystemdClient(user_manager=False) as sd:

            try:
                service_matches = sd.match_units(
                  patterns=self.units,
                  types=["service", "socket", "timer"],
                  include_inactive_files=True
                )
                # self.module.log(f"{service_matches}")

                # {'libvirtd.service': {'enabled': 'enabled', 'active': 'inactive'}, 'libvirtd.socket': {'enabled': 'enabled', 'active': 'active'}}
                mono_states  = {u.name: dict(enabled=u.unit_file_state, active=u.active_state) for u in service_matches if u.name in ["libvirtd.socket", "libvirtd.service"]}
                # {'virtqemud.service': {'enabled': 'disabled', 'active': 'inactive'}, 'virtqemud.socket': {'enabled': 'disabled', 'active': 'inactive'}}
                modu_states  = {u.name: dict(enabled=u.unit_file_state, active=u.active_state) for u in service_matches if u.name in ["virtqemud.socket", "virtqemud.service"]}

                monolithic = self.any_effectively_enabled(mono_states)
                modular = self.any_effectively_enabled(modu_states)

                # self.module.log(f"{mono_states}")
                # self.module.log(f"{modu_states}")

                # self.module.log(f"monolithic: {monolithic}")
                # self.module.log(f"modulate  : {modular}")

                return dict(
                    failed=False,
                    changed=False,
                    monolithic=monolithic,
                    modular=modular
                )

                #for r in results:
                #    self.module.log(f"{r.name:40} {r.kind:7} {r.active_state:10} {r.sub_state:8} {(r.unit_file_state or '-'):10} {(r.load_state or '-'):10} {r.description}")
            except UnitNotFoundError:
                self.module.log("unknown")

        return result_state

    def __disable_services(self, services: list = []):
        """ ... """
        self.module.log(f"LibvirtMonolitic::__disable_services(services: {services})")

        if len(services) != 0:

            _disabled = self.disable(
                user_manager=False,
                services=services,
                service_types=["service", "socket", "timer"],
                include_inactive=True
            )

            self.module.log(f"_disabled: {_disabled}")

            return _disabled
        else:
            return dict(
                failed=False,
                msg="all monolithic service stopped and disabled."
            )

        result_state = []
        service_matches = []

        with SystemdClient(user_manager=False) as sd:
            try:
                service_matches = sd.match_units(
                  patterns=self.units,
                  types=["service", "socket", "timer"],
                  include_inactive_files=True
                )
                self.module.log(f"{service_matches}")
            except UnitNotFoundError:
                self.module.log("unknown")

            self.module.log(f"{service_matches}")

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

    def __enable_services(self):
        """ ... """
        self.module.log("LibvirtMonolitic::__enable_services()")

        _enabled = self.enable(
            user_manager=False,
            services=self.units,
            service_types=["service", "socket", "timer"],
            include_inactive=True
        )

        self.module.log(f"_enabled: {_enabled}")

        return _enabled



        result_state = []
        service_matches = []

        self.module.log("unit files:")
        for u in self.units:
            self.module.log(f"  - {u}")

        with SystemdClient(user_manager=False) as sd:
            try:
                service_matches = sd.match_units(
                  patterns=self.units,
                  types=["service", "socket"],
                  include_inactive_files=True
                )
                # self.module.log(f"{service_matches}")

            except UnitNotFoundError:
                self.module.log("unknown")

            self.module.log(f"service matches: {service_matches}")

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

        return dict(
            failed=False,
            msg="all modular service are enables."
        )

        return dict(
            failed=True,
        )

    def __start_services(self):
        """ ... """
        self.module.log("LibvirtMonolitic::__start_services()")

        _started = self.start(
            user_manager=False,
            services=self.units,
            service_types=["service", "socket", "timer"],
            include_inactive=True
        )

        self.module.log(f"_started: {_started}")

        return _started

        # ----

        result_state = []
        service_matches = []

        with SystemdClient(user_manager=False) as sd:
            try:
                service_matches = sd.match_units(
                  patterns=self.units,
                  types=["service", "socket"],
                  include_inactive_files=True
                )
            except UnitNotFoundError:
                self.module.log("unknown")

            self.module.log(f"{service_matches}")
            # [UnitStatus(name='virtproxyd.service', kind='service', description='', active_state='inactive', sub_state='dead', unit_file_state='enabled', load_state=None, is_enabled=True, is_masked=False)]
            _states  = {u.name: dict(enabled=u.is_enabled, unit_file_state=u.unit_file_state, active_state=u.active_state) for u in service_matches if u.name in self.units}

            for srv, data in _states.items():
                self.module.log(f"- service: {srv} - {data}")

                res = {}

                if sd.exists(srv):
                    unit_state = data.get("enabled", "enabled")
                    active_state = data.get('active_state', 'active')

                    self.module.log(f"   unit state   : {unit_state}")
                    self.module.log(f"   active state : {active_state}")

                    if not active_state == "active" and unit_state:
                        self.module.log(f"   start service: {srv}")
                        try:
                            result = sd.start_wait(unit=srv, timeout_sec=60)
                            self.module.log(f"   result : {result}")

                            res[srv] = dict(
                                changed=True,
                                msg="service sucessfully startet."
                            )

                        except UnitNotFoundError:
                            self.module.log("unknown")
                    else:
                        res[srv] = dict(
                            changed=False,
                            msg="service are running."
                        )

                    result_state.append(res)

        return result_state


        _state, _changed, _failed, state, changed, failed = results(self.module, result_state)

        result = dict(
            changed=_changed,
            failed=False,
            state=result_state
        )

        return result

    def any_effectively_enabled(self, d: dict[str, dict[str, str]]) -> bool:

        enabled_states = {"enabled", "enabled-runtime", "linked", "linked-runtime", "alias"}

        return any((v.get("enabled") or "").lower() in enabled_states for v in d.values())



def main():
    """
    """
    args = dict(
        state=dict(
            choose=[
                "verify",
                "enable",
                "disable",
                "start",
                "stop"
            ],
            default="verify",
            type="str"
        ),
        units=dict(
            required=False,
            default=[],
            type=list
        ),
    )

    module = AnsibleModule(
        argument_spec=args,
        supports_check_mode=False,
    )

    k = LibvirtMonolitic(module)
    result = k.run()

    module.log(msg=f"= result: {result}")

    module.exit_json(**result)


# import module snippets
if __name__ == "__main__":
    main()
