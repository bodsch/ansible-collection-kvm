# -*- coding: utf-8 -*-

# (c) 2020-2025, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import, division, print_function

from ansible_collections.bodsch.systemd.plugins.module_utils.systemd import (
    AccessDeniedError,
    SystemdClient,
    SystemdError,
    UnitNotFoundError,
)


class LibvirtService:
    """
    Shared helper for managing libvirt systemd units, both the monolithic
    'libvirtd' and the modular 'virt*d' daemons.

    Every lifecycle method takes an explicit list of unit names, operates
    idempotently based on the current systemd UnitStatus, and returns a
    ``result_state`` list compatible with bodsch.core ... results()::

        [ {unit_name: {"changed": bool, "failed": bool, ...}}, ... ]
    """

    SERVICE_TYPES = ["service", "socket", "timer"]

    def __init__(self, module, user_manager: bool = False):
        """ """
        self.module = module
        self.user_manager = user_manager
        self.module.log("LibvirtService::__init__()")

    # -- discovery ---------------------------------------------------------

    def _status_map(self, sd, units: list) -> dict:
        """Return ``{unit_name: UnitStatus}`` for the requested units."""
        matches = sd.match_units(
            patterns=units,
            types=self.SERVICE_TYPES,
            include_inactive_files=True,
        )
        return {u.name: u for u in matches if u.name in units}

    def verify(self, units: list) -> dict:
        """Return the current state of each requested unit without changing it."""
        self.module.log(f"LibvirtService::verify(units: {units})")

        with SystemdClient(user_manager=self.user_manager) as sd:
            status = self._status_map(sd, units)

        return {
            name: dict(
                enabled=u.is_enabled,
                unit_file_state=u.unit_file_state,
                active=u.active_state,
                masked=u.is_masked,
            )
            for name, u in status.items()
        }

    # -- lifecycle ---------------------------------------------------------

    def enable(self, units: list, runtime: bool = False) -> list:
        """Unmask (if masked) and enable (if not already enabled) each unit."""
        self.module.log(f"LibvirtService::enable(units: {units}, runtime: {runtime})")
        return self._apply(units, self._enable_one, runtime=runtime)

    def disable(self, units: list) -> list:
        """Stop (if active) and disable (if enabled) each unit."""
        self.module.log(f"LibvirtService::disable(units: {units})")
        return self._apply(units, self._disable_one)

    def start(self, units: list, timeout: float = 60) -> list:
        """Start (and wait for) each unit that is not already active."""
        self.module.log(f"LibvirtService::start(units: {units})")
        return self._apply(units, self._start_one, timeout=timeout)

    def stop(self, units: list) -> list:
        """Stop each unit that is currently active."""
        self.module.log(f"LibvirtService::stop(units: {units})")
        return self._apply(units, self._stop_one)

    # -- internals ---------------------------------------------------------

    def _apply(self, units: list, fn, **kwargs) -> list:
        """
        Open a single SystemdClient connection, look up the state of every
        requested unit and dispatch each one to ``fn``. Units that do not
        exist are reported as skipped; per-unit systemd errors are captured
        as a failure for that unit instead of aborting the whole run.
        """
        result_state = []

        with SystemdClient(user_manager=self.user_manager) as sd:
            status = self._status_map(sd, units)

            for name in units:
                unit = status.get(name)

                if unit is None or not sd.exists(name):
                    self.module.log(f"  - {name}: not present, skipped")
                    result_state.append(
                        {name: dict(changed=False, skipped=True, msg="unit not present")}
                    )
                    continue

                try:
                    result_state.append({name: fn(sd, name, unit, **kwargs)})
                except (UnitNotFoundError, AccessDeniedError, SystemdError) as e:
                    self.module.log(f"  - {name}: {e}")
                    result_state.append(
                        {name: dict(changed=False, failed=True, msg=str(e))}
                    )

        return result_state

    def _enable_one(self, sd, name: str, unit, runtime: bool = False) -> dict:
        """ """
        unmasked = False
        enabled = False

        if unit.is_masked:
            sd.unmask([name])
            unmasked = True

        if not unit.is_enabled:
            sd.enable([name], runtime=runtime)
            enabled = True

        changed = unmasked or enabled

        return dict(
            changed=changed,
            unmasked=unmasked,
            enabled=enabled,
            msg="enabled" if changed else "already enabled",
        )

    def _disable_one(self, sd, name: str, unit, **_) -> dict:
        """ """
        stopped = False
        disabled = False

        if unit.active_state == "active":
            sd.stop(name)
            stopped = True

        if unit.is_enabled:
            sd.disable([name])
            disabled = True

        changed = stopped or disabled

        return dict(
            changed=changed,
            stopped=stopped,
            disabled=disabled,
            msg="disabled" if changed else "already disabled",
        )

    def _start_one(self, sd, name: str, unit, timeout: float = 60, **_) -> dict:
        """ """
        if unit.active_state == "active":
            return dict(changed=False, msg="already running")

        sd.start_wait(unit=name, timeout_sec=timeout)

        return dict(changed=True, msg="started")

    def _stop_one(self, sd, name: str, unit, **_) -> dict:
        """ """
        if unit.active_state != "active":
            return dict(changed=False, msg="already stopped")

        sd.stop(name)

        return dict(changed=True, msg="stopped")
