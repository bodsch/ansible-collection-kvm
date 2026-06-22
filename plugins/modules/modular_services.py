#!/usr/bin/python3
# -*- coding: utf-8 -*-

# (c) 2020-2025, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import, division, print_function

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.bodsch.core.plugins.module_utils.module_results import results
from ansible_collections.bodsch.kvm.plugins.module_utils.libvirt_service import (
    LibvirtService,
)


class LibvirtModular(LibvirtService):
    """
    Manage the modular libvirt daemons (virt*d services and sockets).

    The unit list is supplied by the role via the bodsch.kvm.modular_daemons
    filter; this module only applies the requested lifecycle ``state`` to those
    units.
    """

    def __init__(self, module):
        """ """
        super().__init__(module, user_manager=False)

        self.state = module.params.get("state")
        self.units = module.params.get("units")

    def run(self):
        """ """
        if not self.units:
            return dict(changed=False, failed=False, msg="no units given")

        if self.state == "verify":
            return dict(
                changed=False, failed=False, state=self.verify(self.units)
            )

        dispatch = {
            "enable": self.enable,
            "disable": self.disable,
            "start": self.start,
            "stop": self.stop,
        }

        action = dispatch.get(self.state)

        if action is None:
            return dict(
                changed=False, failed=True, msg=f"unsupported state '{self.state}'"
            )

        result_state = action(self.units)

        _, has_changed, has_failed, _, _, _ = results(self.module, result_state)

        return dict(changed=has_changed, failed=has_failed, state=result_state)


def main():
    """ """
    args = dict(
        state=dict(
            type="str",
            default="verify",
            choices=["verify", "enable", "disable", "start", "stop"],
        ),
        units=dict(type="list", elements="str", required=False, default=[]),
    )

    module = AnsibleModule(
        argument_spec=args,
        supports_check_mode=False,
    )

    k = LibvirtModular(module)
    result = k.run()

    module.exit_json(**result)


# import module snippets
if __name__ == "__main__":
    main()
