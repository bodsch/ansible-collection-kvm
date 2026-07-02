#!/usr/bin/python3
# -*- coding: utf-8 -*-

# (c) 2026, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import, division, print_function

import traceback
from io import BytesIO

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
module: libvirt_cloud_init_iso
author: Bodo Schulz (@bodsch)
version_added: "0.1.0"
short_description: Build cloud-init CIDATA ISO volumes in a libvirt storage pool.
description:
  - Builds a NoCloud / CIDATA seed ISO from cloud-init meta-data, user-data and
    network-config and uploads it as a storage volume into a libvirt pool.
  - A clean, validated replacement for C(community.libvirt.virt_volume) with
    C(create_cidata_cdrom) - the cloud-init payload is passed as typed
    parameters and the ISO is uploaded via a libvirt stream.
  - Takes a list of ISOs and reconciles all of them in a single task, so
    playbooks do not need C(loop).
options:
  uri:
    description:
      - libvirt connection URI.
    type: str
    default: "qemu:///system"
  pool:
    description:
      - Default storage pool for every entry in O(images). Individual entries
        may override it with their own C(pool).
    type: str
    required: true
  images:
    description:
      - List of cloud-init seed ISOs to reconcile.
    type: list
    elements: dict
    required: true
    suboptions:
      name:
        description:
          - Volume name of the ISO inside the pool (e.g. C(web01-cidata.iso)).
        type: str
        required: true
      pool:
        description:
          - Storage pool to create the ISO in. Defaults to the module-level O(pool).
        type: str
      state:
        description:
          - C(present) creates the ISO if it does not exist (existing ISOs are
            left untouched).
          - C(absent) removes the ISO volume.
        type: str
        choices: [present, absent]
        default: present
      metadata:
        description:
          - cloud-init meta-data. A mapping is serialised to YAML; a string is
            written verbatim.
        type: raw
      user_data:
        description:
          - cloud-init user-data. A mapping is serialised to YAML; a string is
            written verbatim. A C(#cloud-config) header is added when missing.
        type: raw
      network_config:
        description:
          - cloud-init network-config. A mapping is serialised to YAML; a
            string is written verbatim. Omit to leave it out of the seed.
        type: raw
requirements:
  - libvirt-python
  - pycdlib
  - PyYAML
notes:
  - Supports C(check_mode).
  - Existing ISO volumes are not rebuilt; remove the volume (C(state=absent)) to
    force regeneration.
  - ISO names should be unique within a single call; the per-image results are
    keyed by name.
"""

EXAMPLES = r"""
- name: build a cloud-init seed ISO for an instance
  bodsch.kvm.libvirt_cloud_init_iso:
    pool: default
    images:
      - name: web01-cidata.iso
        metadata:
          local-hostname: web01
        user_data: "{{ lookup('template', 'cloud_init_debian.yaml.j2') }}"
        network_config:
          version: 2
          ethernets:
            eth0:
              addresses: ["192.168.0.11/24"]
"""

RETURN = r"""
changed:
  description: Whether any ISO was created or removed.
  returned: always
  type: bool
failed:
  description: Whether reconciling any ISO failed.
  returned: always
  type: bool
state:
  description: Per-ISO result, one entry per requested image keyed by name.
  returned: always
  type: list
  elements: dict
"""

if HAS_LIBVIRT:
    import libvirt

PYCDLIB_IMPORT_ERROR = None
try:
    import pycdlib
    HAS_PYCDLIB = True
except ImportError:
    HAS_PYCDLIB = False
    PYCDLIB_IMPORT_ERROR = traceback.format_exc()

YAML_IMPORT_ERROR = None
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    YAML_IMPORT_ERROR = traceback.format_exc()


class LibvirtCloudInitISO:
    """Reconcile a list of cloud-init seed ISO volumes."""

    def __init__(self, module):
        """ """
        self.module = module

        self.uri = module.params.get("uri")
        self.default_pool = module.params.get("pool")
        self.images = module.params.get("images")

    def run(self):
        """ """
        result_state = []

        try:
            with LibvirtConnection(self.uri) as conn:
                pool_cache = {}

                for spec in self.images:
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
            self.module.fail_json(msg=str(e))

        _, has_changed, has_failed, _, _, _ = results(self.module, result_state)

        return dict(changed=has_changed, failed=has_failed, state=result_state)

    # -- dispatch ----------------------------------------------------------

    def _reconcile_one(self, conn, pool_cache, spec):
        """ """
        pool_name = spec.get("pool") or self.default_pool

        pool = pool_cache.get(pool_name)
        if pool is None:
            pool = conn.get_pool(pool_name)
            pool_cache[pool_name] = pool

        name = spec.get("name")
        existing = conn.lookup_volume(pool, name)

        if spec.get("state") == "absent":
            if existing is None:
                return dict(changed=False, msg="already absent")
            if self.module.check_mode:
                return dict(changed=True, msg="would delete cidata iso")
            existing.delete(0)
            return dict(changed=True, msg="deleted")

        # state: present - existing ISOs are not rebuilt
        if existing is not None:
            return dict(changed=False, msg="already present", volume=self._volume_facts(existing))

        if self.module.check_mode:
            return dict(changed=True, msg="would create cidata iso")

        return self._create(conn, pool, spec)

    # -- create ------------------------------------------------------------

    def _create(self, conn, pool, spec):
        """Build the seed ISO and upload it as a new volume."""
        iso_bytes = self._build_iso(spec)

        xml = VolumeXMLBuilder(
            name=spec.get("name"),
            capacity=len(iso_bytes),
            unit="bytes",
            fmt="iso",
        ).to_xml()

        vol = pool.createXML(xml)

        stream = conn.conn.newStream(0)
        vol.upload(stream, 0, len(iso_bytes), 0)
        stream.send(iso_bytes)
        stream.finish()

        return dict(changed=True, msg="created", volume=self._volume_facts(vol))

    def _build_iso(self, spec):
        """Render an ISO9660 (Joliet + Rock Ridge) CIDATA image into bytes."""
        iso = pycdlib.PyCdlib()
        iso.new(interchange_level=3, joliet=True, sys_ident="LINUX", rock_ridge="1.09", vol_ident="cidata")

        network_config = self._render(spec.get("network_config"))
        if network_config is not None:
            self._add_file(iso, network_config, "/NETWORK_CONFIG.;1", "network-config", "/network-config")

        metadata = self._render(spec.get("metadata")) or ""
        self._add_file(iso, metadata, "/METADATA.;1", "meta-data", "/meta-data")

        user_data = self._render_userdata(spec.get("user_data"))
        self._add_file(iso, user_data, "/USERDATA.;1", "user-data", "/user-data")

        out = BytesIO()
        iso.write_fp(out)
        iso.close()
        return out.getvalue()

    def _add_file(self, iso, text, iso_path, rr_name, joliet_path):
        """ """
        data = text.encode("utf-8")
        iso.add_fp(BytesIO(data), len(data), iso_path, rr_name=rr_name, joliet_path=joliet_path)

    def _render(self, value):
        """Serialise a mapping to YAML, pass a string through verbatim."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return yaml.safe_dump(value, width=4096)

    def _render_userdata(self, value):
        """Render user-data, ensuring a #cloud-config header."""
        if value is None:
            return "#cloud-config\n"
        if isinstance(value, str):
            if value.lstrip().startswith("#cloud-config"):
                return value
            return "#cloud-config\n" + value
        return "#cloud-config\n" + yaml.safe_dump(value, width=4096)

    # -- helpers -----------------------------------------------------------

    def _volume_facts(self, vol):
        """ """
        return dict(name=vol.name(), path=vol.path(), key=vol.key())


def main():
    """ """
    image_suboptions = dict(
        name=dict(type="str", required=True),
        pool=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        metadata=dict(type="raw"),
        user_data=dict(type="raw"),
        network_config=dict(type="raw"),
    )

    args = dict(
        uri=dict(type="str", default="qemu:///system"),
        pool=dict(type="str", required=True),
        images=dict(
            type="list",
            elements="dict",
            required=True,
            options=image_suboptions,
        ),
    )

    module = AnsibleModule(
        argument_spec=args,
        supports_check_mode=True,
    )

    if not HAS_LIBVIRT:
        module.fail_json(msg=missing_required_lib("libvirt-python"), exception=LIBVIRT_IMPORT_ERROR)
    if not HAS_PYCDLIB:
        module.fail_json(msg=missing_required_lib("pycdlib"), exception=PYCDLIB_IMPORT_ERROR)
    if not HAS_YAML:
        module.fail_json(msg=missing_required_lib("PyYAML"), exception=YAML_IMPORT_ERROR)

    try:
        c = LibvirtCloudInitISO(module)
        result = c.run()
    except Exception as e:  # pragma: no cover - defensive
        module.fail_json(msg=f"unexpected error: {e}", exception=traceback.format_exc())

    module.exit_json(**result)


# import module snippets
if __name__ == "__main__":
    main()
