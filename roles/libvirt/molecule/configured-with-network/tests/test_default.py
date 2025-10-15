# coding: utf-8
from __future__ import unicode_literals

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar

import json
import pytest
import os

import testinfra.utils.ansible_runner

HOST = 'instance'

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts(HOST)


def pp_json(json_thing, sort=True, indents=2):
    if type(json_thing) is str:
        print(json.dumps(json.loads(json_thing), sort_keys=sort, indent=indents))
    else:
        print(json.dumps(json_thing, sort_keys=sort, indent=indents))
    return None


def base_directory():
    """
    """
    cwd = os.getcwd()

    if 'group_vars' in os.listdir(cwd):
        directory = "../.."
        molecule_directory = "."
    else:
        directory = "."
        molecule_directory = f"molecule/{os.environ.get('MOLECULE_SCENARIO_NAME')}"

    return directory, molecule_directory


def read_ansible_yaml(file_name, role_name):
    """
    """
    read_file = None

    for e in ["yml", "yaml"]:
        test_file = f"{file_name}.{e}"
        if os.path.isfile(test_file):
            read_file = test_file
            break

    return f"file={read_file} name={role_name}"


@pytest.fixture()
def get_vars(host):
    """
        parse ansible variables
        - defaults/main.yml
        - vars/main.yml
        - vars/${DISTRIBUTION}.yaml
        - molecule/${MOLECULE_SCENARIO_NAME}/group_vars/all/vars.yml
    """
    base_dir, molecule_dir = base_directory()
    distribution = host.system_info.distribution
    operation_system = None

    if distribution in ['debian', 'ubuntu']:
        operation_system = "debian"
    elif distribution in ['redhat', 'ol', 'centos', 'rocky', 'almalinux']:
        operation_system = "redhat"
    elif distribution in ['arch', 'artix']:
        operation_system = f"{distribution}linux"

    # print(" -> {} / {}".format(distribution, os))
    # print(" -> {}".format(base_dir))

    file_defaults      = read_ansible_yaml(f"{base_dir}/defaults/main", "role_defaults")
    file_vars          = read_ansible_yaml(f"{base_dir}/vars/main", "role_vars")
    file_distibution   = read_ansible_yaml(f"{base_dir}/vars/{operation_system}", "role_distibution")
    file_molecule      = read_ansible_yaml(f"{molecule_dir}/group_vars/all/vars", "test_vars")
    # file_host_molecule = read_ansible_yaml("{}/host_vars/{}/vars".format(base_dir, HOST), "host_vars")

    defaults_vars      = host.ansible("include_vars", file_defaults).get("ansible_facts").get("role_defaults")
    vars_vars          = host.ansible("include_vars", file_vars).get("ansible_facts").get("role_vars")
    distibution_vars   = host.ansible("include_vars", file_distibution).get("ansible_facts").get("role_distibution")
    molecule_vars      = host.ansible("include_vars", file_molecule).get("ansible_facts").get("test_vars")
    # host_vars          = host.ansible("include_vars", file_host_molecule).get("ansible_facts").get("host_vars")

    ansible_vars = defaults_vars
    ansible_vars.update(vars_vars)
    ansible_vars.update(distibution_vars)
    ansible_vars.update(molecule_vars)
    # ansible_vars.update(host_vars)

    templar = Templar(loader=DataLoader(), variables=ansible_vars)
    result = templar.template(ansible_vars, fail_on_undefined=False)

    return result


@pytest.mark.parametrize("dirs", [
    "/etc/libvirt",
    "/etc/libvirt/qemu",
    "/etc/libvirt/storage"
])
def test_directories(host, dirs):
    d = host.file(dirs)
    assert d.is_directory


@pytest.mark.parametrize("files", [
    "/etc/libvirt/libvirtd.conf",
    "/etc/libvirt/qemu.conf",
    "/etc/libvirt/qemu/networks/default.xml",
    "/etc/libvirt/storage/pool.xml",
])
def test_files(host, files):
    f = host.file(files)
    assert f.exists


def test_qemu_conf(host, get_vars):
    """
    """
    import re
    security_driver = "security_driver.* = \"none\""
    vnc_listen      = "vnc_listen .* = \"127.0.0.1\""
    config_file = host.file("/etc/libvirt/qemu.conf")

    assert config_file.is_file

    content = config_file.content_string.split("\n")
    reg_security_driver = re.compile(security_driver)
    reg_vnc_listen = re.compile(vnc_listen)

    assert (len(list(filter(reg_security_driver.match, content))) > 0)
    assert (len(list(filter(reg_vnc_listen.match, content))) > 0)


def test_libvirt_conf(host, get_vars):
    """
    """
    _conf_libvirtd = get_vars.get("libvirt_libvirtd", {})
    _conf_libvirtd_tcp_port = _conf_libvirtd.get("tcp_port", None)

    if not _conf_libvirtd_tcp_port:
        assert False, "TCP is enabled, but no port ist configured"

    log_outputs = 'log_outputs               = "2:file:/var/log/libvirt/libvirtd.log 3:journald"'
    listen_tcp = 'listen_tcp                = 1'
    listen_tcp_port = f'tcp_port                  = "{_conf_libvirtd_tcp_port}"'

    config_file = host.file("/etc/libvirt/libvirtd.conf")

    assert config_file.is_file

    assert log_outputs in config_file.content_string
    assert listen_tcp in config_file.content_string
    assert listen_tcp_port in config_file.content_string


def test_service_running_and_enabled(host, get_vars):
    """
      running service
    """
    service = host.service("libvirtd")
    assert service.is_running
    assert service.is_enabled


def test_listening_socket(host, get_vars):
    """
    """
    listening = host.socket.get_listening_sockets()

    for i in listening:
        print(i)

    _conf_libvirtd = get_vars.get("libvirt_libvirtd", {})
    _conf_libvirtd_tcp = _conf_libvirtd.get("enable_tcp", True)

    listen = []

    if _conf_libvirtd_tcp:
        _conf_libvirtd_tcp_port = _conf_libvirtd.get("tcp_port", None)

        if not _conf_libvirtd_tcp_port:
            assert False, "TCP is enabled, but no port ist configured"

        listen.append(f"tcp://0.0.0.0:{_conf_libvirtd_tcp_port}")

    for spec in listen:
        socket = host.socket(spec)
        assert socket.is_listening
