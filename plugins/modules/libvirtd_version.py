#!/usr/bin/python3
# -*- coding: utf-8 -*-

# (c) 2023, Bodo Schulz <bodo@boone-schulz.de>

from __future__ import absolute_import, division, print_function
import re

from ansible.module_utils.basic import AnsibleModule


class Libvirtd(object):
    """
    """
    module = None

    def __init__(self, module):
        """
        """
        self.module = module

        self.libvirtd_bin = module.get_bin_path('libvirtd', True)

    def version(self):
        """
            # # libvirtd --version
            # libvirtd (libvirt) 11.8.0
        """
        _failed = True
        _version = "unknown"
        _stdout = ""
        _stdout_lines = []

        args = []

        args.append(self.libvirtd_bin)
        args.append("--version")

        rc, out = self._exec(args)

        if "libvirtd" in out:
            pattern = re.compile(r".*libvirtd \(.*\) (?P<version>[0-9]+\.[0-9]+\.[0-9]+).*", re.MULTILINE)
            found = re.search(pattern, out.rstrip())

            if found:
                _version = found.group('version')
                _failed = False
        else:
            _failed = True

        _stdout = f"{out.rstrip()}"
        _stdout_lines = _stdout.split("\n")

        return dict(
            stdout=_stdout,
            stdout_lines=_stdout_lines,
            failed=_failed,
            version=_version
        )

    def _exec(self, commands):
        """
        """
        rc, out, err = self.module.run_command(commands, check_rc=False)

        if int(rc) != 0:
            self.module.log(msg=f"  rc : '{rc}'")
            self.module.log(msg=f"  out: '{out}'")
            self.module.log(msg=f"  err: '{err}'")

        return rc, out


def main():

    args = dict()

    module = AnsibleModule(
        argument_spec=args,
        supports_check_mode=False,
    )

    m = Libvirtd(module)
    result = m.version()

    module.log(f"= result: {result}")

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
