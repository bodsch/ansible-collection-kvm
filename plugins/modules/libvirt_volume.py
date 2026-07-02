#!/usr/bin/python3
# -*- coding: utf-8 -*-

# (c) 2026, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import, division, print_function

import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.bodsch.core.plugins.module_utils.module_results import results
from ansible_collections.bodsch.kvm.plugins.module_utils.libvirt_connection import (
    HAS_LIBVIRT,
    LIBVIRT_IMPORT_ERROR,
    LibvirtConnection,
    LibvirtConnectionError,
)
from ansible_collections.bodsch.kvm.plugins.module_utils.libvirt_xml import (
    VolumeXMLBuilder,
    XMLValidationError,
)

DOCUMENTATION = r"""
---
module: libvirt_volume
author: Bodo Schulz (@bodsch)
version_added: "0.1.0"
short_description: Manage a set of libvirt storage volumes from structured parameters.
description:
  - Creates, clones, resizes and deletes libvirt storage volumes inside a
    storage pool.
  - A clean, validated replacement for the C(create) and C(delete) commands of
    C(community.libvirt.virt_volume) - each volume is described by typed
    parameters instead of a freestyle C(xml) block, and the XML is built and
    validated by the module before it reaches the hypervisor.
  - Takes a list of volume definitions and reconciles all of them in a single
    task, so playbooks do not need C(loop).
options:
  uri:
    description:
      - libvirt connection URI.
    type: str
    default: "qemu:///system"
  pool:
    description:
      - Default storage pool for every entry in O(volumes). Individual entries
        may override it with their own C(pool).
    type: str
    required: true
  volumes:
    description:
      - List of storage volumes to reconcile.
    type: list
    elements: dict
    required: true
    suboptions:
      name:
        description:
          - Name of the storage volume (the file name within the pool).
        type: str
        required: true
      pool:
        description:
          - Storage pool this volume lives in. Defaults to the module-level O(pool).
        type: str
      state:
        description:
          - C(present) ensures the volume exists (creating, optionally cloning,
            and resizing it as needed).
          - C(absent) ensures the volume does not exist.
        type: str
        choices: [present, absent]
        default: present
      capacity:
        description:
          - Logical capacity of the volume, interpreted together with C(unit).
          - Required when C(state=present).
        type: int
      unit:
        description:
          - Unit for C(capacity) and C(allocation). Bare and C(*iB) units are
            binary (1024-based), C(*B) units are decimal (1000-based).
        type: str
        default: "G"
        choices: [B, bytes, KB, K, KiB, MB, M, MiB, GB, G, GiB, TB, T, TiB]
      format:
        description:
          - Target image format of the volume.
        type: str
        default: qcow2
        choices: [raw, qcow2, qcow, qed, vmdk, vdi, vpc, iso]
      allocation:
        description:
          - Initial allocation of the volume, in C(unit). Omit for a sparse volume.
        type: int
      clone_source:
        description:
          - Name of an existing volume in the same pool to clone from when the
            target volume is created. Ignored if the volume already exists.
        type: str
      resize:
        description:
          - When the volume already exists and its capacity differs from
            C(capacity), resize it to match. Set to V(false) to leave existing
            volumes untouched.
        type: bool
        default: true
      wipe:
        description:
          - When C(state=absent), wipe the volume contents before deleting it.
        type: bool
        default: false
requirements:
  - libvirt-python
notes:
  - Supports C(check_mode).
  - Volume names should be unique within a single call; the per-volume results
    are keyed by name.
"""

EXAMPLES = r"""
- name: reconcile the disks of an instance in one task
  bodsch.kvm.libvirt_volume:
    pool: default
    volumes:
      - name: web01-os.qcow2
        capacity: 20
        clone_source: debian-12-base.qcow2
      - name: web01-data.qcow2
        capacity: 50
      - name: web01-scratch.qcow2
        state: absent
        wipe: true
"""

RETURN = r"""
changed:
  description: Whether any volume was created, resized or deleted.
  returned: always
  type: bool
failed:
  description: Whether reconciling any volume failed.
  returned: always
  type: bool
state:
  description: Per-volume result, one entry per requested volume keyed by name.
  returned: always
  type: list
  elements: dict
  sample:
    - web01-os.qcow2:
        changed: true
        msg: created
        volume:
          name: web01-os.qcow2
          path: /var/lib/libvirt/images/web01-os.qcow2
          key: /var/lib/libvirt/images/web01-os.qcow2
          capacity_bytes: 21474836480
"""

if HAS_LIBVIRT:
    import libvirt

CAPACITY_UNIT_CHOICES = [
    "B", "bytes", "KB", "K", "KiB", "MB", "M", "MiB", "GB", "G", "GiB", "TB", "T", "TiB",
]
VOLUME_FORMAT_CHOICES = ["raw", "qcow2", "qcow", "qed", "vmdk", "vdi", "vpc", "iso"]


class LibvirtVolume:
    """Reconcile a list of libvirt storage volumes against the requested state."""

    def __init__(self, module):
        """ """
        self.module = module

        self.uri = module.params.get("uri")
        self.default_pool = module.params.get("pool")
        self.volumes = module.params.get("volumes")

    def run(self):
        """ """
        result_state = []

        try:
            with LibvirtConnection(self.uri) as conn:
                pool_cache = {}

                for spec in self.volumes:
                    name = spec.get("name")
                    try:
                        result_state.append({name: self._reconcile_one(conn, pool_cache, spec)})
                    except (LibvirtConnectionError, XMLValidationError) as e:
                        result_state.append({name: dict(changed=False, failed=True, msg=str(e))})
                    except libvirt.libvirtError as e:
                        result_state.append(
                            {name: dict(changed=False, failed=True, msg=f"libvirt error: {e.get_error_message()}")}
                        )

        except LibvirtConnectionError as e:
            # connection-level failure affects every volume: fail hard.
            self.module.fail_json(msg=str(e))

        _, has_changed, has_failed, _, _, _ = results(self.module, result_state)

        return dict(changed=has_changed, failed=has_failed, state=result_state)

    # -- dispatch ----------------------------------------------------------

    def _reconcile_one(self, conn, pool_cache, spec):
        """Resolve the pool for one volume spec and reconcile it."""
        pool_name = spec.get("pool") or self.default_pool

        pool = pool_cache.get(pool_name)
        if pool is None:
            pool = conn.get_pool(pool_name)
            pool_cache[pool_name] = pool

        if spec.get("state") == "absent":
            return self._absent_one(conn, pool, spec)

        return self._present_one(conn, pool, spec)

    # -- state: present ----------------------------------------------------

    def _present_one(self, conn, pool, spec):
        """Ensure one volume exists, cloning and/or resizing as required."""
        builder = VolumeXMLBuilder(
            name=spec.get("name"),
            capacity=spec.get("capacity"),
            unit=spec.get("unit"),
            fmt=spec.get("format"),
            allocation=spec.get("allocation"),
        )
        xml = builder.to_xml()
        target_bytes = builder.capacity_bytes()

        existing = conn.lookup_volume(pool, spec.get("name"))

        if existing is None:
            return self._create_one(conn, pool, spec, xml, target_bytes)

        return self._reconcile_existing(spec, existing, target_bytes)

    def _create_one(self, conn, pool, spec, xml, target_bytes):
        """Create (optionally clone) a volume that does not yet exist."""
        clone_source = spec.get("clone_source")
        clone_src_vol = None

        if clone_source:
            clone_src_vol = conn.lookup_volume(pool, clone_source)
            if clone_src_vol is None:
                return dict(
                    changed=False,
                    failed=True,
                    msg=f"clone source volume '{clone_source}' does not exist in pool '{pool.name()}'",
                )

        if self.module.check_mode:
            return dict(
                changed=True,
                msg="would create volume",
                volume=dict(name=spec.get("name"), capacity_bytes=target_bytes),
            )

        if clone_src_vol is not None:
            vol = pool.createXMLFrom(xml, clone_src_vol, 0)
        else:
            vol = pool.createXML(xml)

        return dict(changed=True, msg="created", volume=self._volume_facts(vol, target_bytes))

    def _reconcile_existing(self, spec, vol, target_bytes):
        """Resize an existing volume if its capacity drifts from the request."""
        changed = False
        msg = "present"

        if spec.get("resize"):
            current_bytes = vol.info()[1]
            if current_bytes != target_bytes:
                if not self.module.check_mode:
                    vol.resize(target_bytes)
                changed = True
                msg = "resized"

        return dict(changed=changed, msg=msg, volume=self._volume_facts(vol, target_bytes))

    # -- state: absent -----------------------------------------------------

    def _absent_one(self, conn, pool, spec):
        """Ensure one volume does not exist."""
        existing = conn.lookup_volume(pool, spec.get("name"))

        if existing is None:
            return dict(changed=False, msg="already absent")

        if self.module.check_mode:
            return dict(changed=True, msg="would delete volume")

        if spec.get("wipe"):
            existing.wipe(0)

        existing.delete(0)

        return dict(changed=True, msg="deleted")

    # -- helpers -----------------------------------------------------------

    def _volume_facts(self, vol, target_bytes):
        """ """
        return dict(
            name=vol.name(),
            path=vol.path(),
            key=vol.key(),
            capacity_bytes=target_bytes,
        )


def main():
    """ """
    volume_suboptions = dict(
        name=dict(type="str", required=True),
        pool=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        capacity=dict(type="int"),
        unit=dict(type="str", default="G", choices=CAPACITY_UNIT_CHOICES),
        format=dict(type="str", default="qcow2", choices=VOLUME_FORMAT_CHOICES),
        allocation=dict(type="int"),
        clone_source=dict(type="str"),
        resize=dict(type="bool", default=True),
        wipe=dict(type="bool", default=False),
    )

    args = dict(
        uri=dict(type="str", default="qemu:///system"),
        pool=dict(type="str", required=True),
        volumes=dict(
            type="list",
            elements="dict",
            required=True,
            options=volume_suboptions,
            required_if=[
                ["state", "present", ["capacity"]],
            ],
        ),
    )

    module = AnsibleModule(
        argument_spec=args,
        supports_check_mode=True,
    )

    if not HAS_LIBVIRT:
        module.fail_json(
            msg=missing_required_lib("libvirt-python"),
            exception=LIBVIRT_IMPORT_ERROR,
        )

    try:
        v = LibvirtVolume(module)
        result = v.run()
    except Exception as e:  # pragma: no cover - defensive
        module.fail_json(msg=f"unexpected error: {e}", exception=traceback.format_exc())

    module.exit_json(**result)


# import module snippets
if __name__ == "__main__":
    main()
