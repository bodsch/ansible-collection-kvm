# coding: utf-8
from __future__ import annotations, unicode_literals

from helper.molecule import get_vars, infra_hosts

testinfra_hosts = infra_hosts(host_name="instance")

CONNECT = "virsh --connect qemu:///system"

# --- tests -----------------------------------------------------------------


def test_images_registered_as_volumes(host, get_vars):
    """downloaded images must show up as volumes after the pool refresh"""
    pool = get_vars.get("base_images_libvirt", {}).get("pool", "default")
    listing = host.run(f"{CONNECT} vol-list {pool}").stdout
    for img in get_vars.get("base_images", []):
        assert img["dest"] in listing


def test_image_files_on_disk(host, get_vars):
    """the image files must exist in the pool's target directory"""
    pools = {p["name"]: p for p in get_vars.get("storage_pools", [])}
    pool_name = get_vars.get("base_images_libvirt", {}).get("pool", "default")
    pool_path = pools.get(pool_name, {}).get("path")
    assert pool_path, "pool path not resolvable from storage_pools"
    for img in get_vars.get("base_images", []):
        assert host.file(f"{pool_path}/{img['dest']}").exists
