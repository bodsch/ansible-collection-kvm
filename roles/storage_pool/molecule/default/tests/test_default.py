# coding: utf-8
from __future__ import annotations, unicode_literals

from helper.molecule import get_vars, infra_hosts

testinfra_hosts = infra_hosts(host_name="instance")

CONNECT = "virsh --connect qemu:///system"

# --- tests -----------------------------------------------------------------


def test_pool_paths(host, get_vars):
    """the role must create the target directory of every non-absent pool"""
    for pool in get_vars.get("storage_pools", []):
        if pool.get("state") == "absent" or "path" not in pool:
            continue
        assert host.file(pool["path"]).is_directory


def test_pools_defined(host, get_vars):
    """every non-absent pool must be known to libvirt"""
    listing = host.run(f"{CONNECT} pool-list --all").stdout
    for pool in get_vars.get("storage_pools", []):
        if pool.get("state") == "absent":
            continue
        assert pool["name"] in listing


def test_pools_active(host, get_vars):
    """pools declared state: active must be running"""
    for pool in get_vars.get("storage_pools", []):
        if pool.get("state") != "active":
            continue
        info = host.run(f"{CONNECT} pool-info {pool['name']}")
        assert info.rc == 0
        assert "running" in info.stdout.lower()
