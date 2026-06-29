# -*- coding: utf-8 -*-

# (c) 2026, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

"""
Shared libvirt connection helper for the bodsch.kvm modules.

This wraps the libvirt-python bindings in a small context manager and a set of
``lookup_*`` helpers that translate libvirt's "not found" error codes into a
plain ``None`` while surfacing every other failure as a single
``LibvirtConnectionError`` carrying a clean, human readable message.

The helper is intentionally free of any AnsibleModule reference so the lookup
and connection logic stays unit-testable without a running hypervisor; the
calling module is responsible for turning ``LibvirtConnectionError`` into
``fail_json`` and for the ``missing_required_lib`` guard via ``HAS_LIBVIRT``.
"""

from __future__ import absolute_import, division, print_function

import traceback

LIBVIRT_IMPORT_ERROR = None
try:
    import libvirt
    HAS_LIBVIRT = True
except ImportError:
    HAS_LIBVIRT = False
    LIBVIRT_IMPORT_ERROR = traceback.format_exc()


class LibvirtConnectionError(Exception):
    """Raised for any libvirt connection or lookup failure with a clean message."""

    pass


class LibvirtConnection:
    """
    Context manager around a read-write libvirt connection.

    Usage::

        with LibvirtConnection(uri) as conn:
            pool = conn.get_pool("default")
            vol = conn.lookup_volume(pool, "disk.qcow2")
    """

    def __init__(self, uri):
        """ """
        self.uri = uri
        self.conn = None

    def __enter__(self):
        """ """
        try:
            self.conn = libvirt.open(self.uri)
        except libvirt.libvirtError as e:
            raise LibvirtConnectionError(
                f"failed to open libvirt connection to '{self.uri}': {e.get_error_message()}"
            )

        if self.conn is None:
            raise LibvirtConnectionError(
                f"failed to open libvirt connection to '{self.uri}'"
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ """
        if self.conn is not None:
            try:
                self.conn.close()
            except libvirt.libvirtError:
                pass

        # never swallow exceptions raised inside the with-block
        return False

    # -- storage pool ------------------------------------------------------

    def lookup_pool(self, name):
        """Return the storage pool object, or ``None`` if it does not exist."""
        try:
            return self.conn.storagePoolLookupByName(name)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_POOL:
                return None
            raise LibvirtConnectionError(
                f"failed to look up storage pool '{name}': {e.get_error_message()}"
            )

    def get_pool(self, name):
        """Return the storage pool object, or raise if it does not exist."""
        pool = self.lookup_pool(name)
        if pool is None:
            raise LibvirtConnectionError(f"storage pool '{name}' not found")
        return pool

    def define_pool(self, xml):
        """Define (persistently register) a storage pool from its XML."""
        try:
            return self.conn.storagePoolDefineXML(xml)
        except libvirt.libvirtError as e:
            raise LibvirtConnectionError(
                f"failed to define storage pool: {e.get_error_message()}"
            )

    # -- storage volume ----------------------------------------------------

    def lookup_volume(self, pool, name):
        """Return the volume object within ``pool``, or ``None`` if it does not exist."""
        try:
            return pool.storageVolLookupByName(name)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_VOL:
                return None
            raise LibvirtConnectionError(
                f"failed to look up volume '{name}' in pool '{pool.name()}': {e.get_error_message()}"
            )

    # -- virtual network ---------------------------------------------------

    def lookup_network(self, name):
        """Return the virtual network object, or ``None`` if it does not exist."""
        try:
            return self.conn.networkLookupByName(name)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_NETWORK:
                return None
            raise LibvirtConnectionError(
                f"failed to look up network '{name}': {e.get_error_message()}"
            )

    def define_network(self, xml):
        """Define (persistently register) a virtual network from its XML."""
        try:
            return self.conn.networkDefineXML(xml)
        except libvirt.libvirtError as e:
            raise LibvirtConnectionError(
                f"failed to define network: {e.get_error_message()}"
            )

    # -- domain ------------------------------------------------------------

    def lookup_domain(self, name):
        """Return the domain object, or ``None`` if it does not exist."""
        try:
            return self.conn.lookupByName(name)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                return None
            raise LibvirtConnectionError(
                f"failed to look up domain '{name}': {e.get_error_message()}"
            )

    def define_domain(self, xml):
        """Define (persistently register) a domain from its XML."""
        try:
            return self.conn.defineXML(xml)
        except libvirt.libvirtError as e:
            raise LibvirtConnectionError(
                f"failed to define domain: {e.get_error_message()}"
            )
