# coding: utf-8
from __future__ import annotations, unicode_literals

import os
import pytest
import testinfra.utils.ansible_runner
from helper.molecule import get_vars, infra_hosts, local_facts

testinfra_hosts = infra_hosts(host_name="instance")

# --- tests -----------------------------------------------------------------

# _facts = local_facts(host=host, fact="libvirt")

@pytest.mark.parametrize(
    "dirs",
    [
        "/etc/libvirt",
        "/etc/libvirt/qemu",
    ],
)
def test_directories(host, dirs):
    d = host.file(dirs)
    assert d.is_directory


@pytest.mark.parametrize(
    "files",
    [
        "/etc/libvirt/libvirt-admin.conf",
        "/etc/libvirt/libvirt.conf",
        "/etc/libvirt/libvirtd.conf",
        "/etc/libvirt/qemu.conf",
        "/etc/libvirt/lxc.conf",
        "/etc/libvirt/virtchd.conf",
        "/etc/libvirt/virtinterfaced.conf",
        "/etc/libvirt/virtlockd.conf",
        "/etc/libvirt/virtlogd.conf",
        "/etc/libvirt/virtlxcd.conf",
        "/etc/libvirt/virtnetworkd.conf",
        "/etc/libvirt/virtnodedevd.conf",
        "/etc/libvirt/virtnwfilterd.conf",
        "/etc/libvirt/virtproxyd.conf",
        "/etc/libvirt/virtqemud.conf",
        "/etc/libvirt/virtsecretd.conf",
        "/etc/libvirt/virtstoraged.conf",
        "/etc/libvirt/virtvboxd.conf",
        "/etc/libvirt/qemu/networks/default.xml",
    ],
)
def test_files(host, files):
    f = host.file(files)
    assert f.exists


@pytest.mark.parametrize(
    "files",
    [
        "/etc/systemd/system/sockets.target.wants/virtlockd-admin.socket",
        "/etc/systemd/system/sockets.target.wants/virtlogd-admin.socket",
        "/etc/systemd/system/sockets.target.wants/virtlogd.socket",
    ],
)
def test_activated_sockets(host, files):
    f = host.file(files)
    assert f.exists


@pytest.mark.parametrize(
    "files",
    [
        "/etc/systemd/system/sockets.target.wants/libvirtd.socket",
        "/etc/systemd/system/sockets.target.wants/libvirtd-ro.socket",
        "/etc/systemd/system/sockets.target.wants/libvirtd-admin.socket",
        "/etc/systemd/system/sockets.target.wants/libvirtd-tcp.socket",
    ],
)
def test_removed_sockets(host, files):
    f = host.file(files)
    assert not f.exists
