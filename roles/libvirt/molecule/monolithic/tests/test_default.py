# coding: utf-8
from __future__ import annotations, unicode_literals

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
        # "/etc/libvirt/hooks",
    ],
)
def test_directories(host, dirs):
    d = host.file(dirs)
    assert d.is_directory


# def test_files(host):
#
#     _version = version(host)
#
#     print(f"installed version: {_version}")
#
#     static_files = [
#         "/etc/libvirt/libvirt-admin.conf",
#         "/etc/libvirt/libvirt.conf",
#         "/etc/libvirt/libvirtd.conf",
#         "/etc/libvirt/qemu.conf",
#         # "/etc/libvirt/lxc.conf",
#         "/etc/libvirt/qemu/networks/default.xml",
#     ]
#
#     # modular > version 10.
#     if Version(_version) < Version("9.0"):
#
#         _files = [
#             "/etc/libvirt/virtchd.conf",
#             "/etc/libvirt/virtinterfaced.conf",
#             "/etc/libvirt/virtlockd.conf",
#             "/etc/libvirt/virtlogd.conf",
#             "/etc/libvirt/virtlxcd.conf",
#             "/etc/libvirt/virtnetworkd.conf",
#             "/etc/libvirt/virtnodedevd.conf",
#             "/etc/libvirt/virtnwfilterd.conf",
#             "/etc/libvirt/virtproxyd.conf",
#             "/etc/libvirt/virtqemud.conf",
#             "/etc/libvirt/virtsecretd.conf",
#             "/etc/libvirt/virtstoraged.conf",
#             "/etc/libvirt/virtvboxd.conf",
#         ]
#
#         static_files += _files
#
#     else:
#         _files = [
#             "/etc/libvirt/network.conf",
#         ]
#
#         static_files += _files
#
#     for x in static_files:
#         print(f" - {x}")
#         f = host.file(x)
#         assert f.exists
#
#
# def test_sockets(host):
#     """
#     # tree  /run/libvirt/
#     /run/libvirt/
#     |-- common
#     |   `-- system.token
#     |-- hostdevmgr
#     |-- interface
#     |-- libvirt-admin-sock
#     |-- libvirt-sock
#     |-- libvirt-sock-ro
#     |-- lxc
#     |   `-- autostarted
#     |-- network
#     |   |-- autostarted
#     |   `-- nwfilter.leases
#     |-- nodedev
#     |-- nwfilter
#     |-- nwfilter-binding
#     |-- qemu
#     |   |-- autostarted
#     |   |-- dbus
#     |   |-- passt
#     |   `-- slirp
#     |-- secrets
#     |-- storage
#     |   |-- autostarted
#     |   `-- pool.xml
#     |-- virtlockd-sock
#     `-- virtlogd-sock
#
#     """
#     _version = version(host)
#
#     print(f"installed version: {_version}")
#
#     _sockets = []
#
#     # modular > version 10.
#     if Version(_version) <= Version("9.0"):
#         _sockets = [
#             "/run/libvirt/libvirt-admin-sock",
#             "/run/libvirt/libvirt-sock",
#             "/run/libvirt/libvirt-sock-ro",
#             "/run/libvirt/virtlockd-sock",
#             "/run/libvirt/virtlogd-sock",
#             # "/run/libvirt/",
#             # "/run/libvirt/",
#             # "/run/libvirt/",
#         ]
#
#     for x in _sockets:
#         print(f" - {x}")
#         f = host.file(x)
#         assert f.exists
#
#
# def test_systemd(host):
#     """
#     # tree /etc/systemd/system/
#     /etc/systemd/system/
#     |-- default.target -> /lib/systemd/system/multi-user.target
#     |-- multi-user.target.wants
#     |   |-- libvirt-guests.service -> /lib/systemd/system/libvirt-guests.service
#     |   |-- libvirtd.service -> /lib/systemd/system/libvirtd.service
#     |-- sockets.target.wants
#     |   |-- libvirtd-admin.socket -> /lib/systemd/system/libvirtd-admin.socket
#     |   |-- libvirtd-ro.socket -> /lib/systemd/system/libvirtd-ro.socket
#     |   |-- libvirtd-tcp.socket -> /lib/systemd/system/libvirtd-tcp.socket
#     |   |-- libvirtd.socket -> /lib/systemd/system/libvirtd.socket
#     |   |-- virtlockd-admin.socket -> /lib/systemd/system/virtlockd-admin.socket
#     |   |-- virtlockd.socket -> /lib/systemd/system/virtlockd.socket
#     |   |-- virtlogd-admin.socket -> /lib/systemd/system/virtlogd-admin.socket
#     |   `-- virtlogd.socket -> /lib/systemd/system/virtlogd.socket
#     |-- sshd.service -> /lib/systemd/system/ssh.service
#     |-- sysinit.target.wants
#     `-- timers.target.wants
#
#     """
#     _version = version(host)
#
#     print(f"installed version: {_version}")
#
#     systemd = []
#
#     # modular > version 10.
#     if Version(_version) < Version("9.0"):
#
#         systemd = [
#             "/etc/systemd/system/multi-user.target.wants/libvirtd.service",
#             "/etc/systemd/system/sockets.target.wants/libvirtd-admin.socket",
#             "/etc/systemd/system/sockets.target.wants/libvirtd-ro.socket",
#             "/etc/systemd/system/sockets.target.wants/libvirtd-tcp.socket",
#             "/etc/systemd/system/sockets.target.wants/libvirtd.socket",
#             "/etc/systemd/system/sockets.target.wants/virtlockd-admin.socket",
#             "/etc/systemd/system/sockets.target.wants/virtlockd.socket",
#             "/etc/systemd/system/sockets.target.wants/virtlogd-admin.socket",
#             "/etc/systemd/system/sockets.target.wants/virtlogd.socket",
#             # "/etc/systemd/system/sockets.target.wants/",
#             # "/etc/systemd/system/sockets.target.wants/",
#             # "/etc/systemd/system/sockets.target.wants/",
#         ]
#
#     for x in systemd:
#         print(f" - {x}")
#         f = host.file(x)
#         assert f.exists
#
#
# def test_qemu_conf(host, get_vars):
#     """ """
#     _version = version(host)
#
#     print(f"installed version: {_version}")
#
#     # modular > version 10.
#     if Version(_version) < Version("9.0"):
#
#         config_file = "/etc/libvirt/qemu.conf"
#
#         security_driver = 'security_driver.* = "none"'
#         vnc_listen = 'vnc_listen .* = "127.0.0.1"'
#         config_file = host.file(config_file)
#         # assert config_file.is_file
#
#         content = config_file.content_string.split("\n")
#         reg_security_driver = re.compile(security_driver)
#         reg_vnc_listen = re.compile(vnc_listen)
#
#         assert len(list(filter(reg_security_driver.match, content))) > 0
#         assert len(list(filter(reg_vnc_listen.match, content))) > 0
#
#     else:
#         config_file = "/etc/libvirt/virtproxyd.conf"


# def test_libvirt_conf(host, get_vars):
#     """ """
#     _version = version(host)
#
#     print(f"installed version: {_version}")
#
#     # modular > version 10.
#     if Version(_version) < Version("9.0"):
#
#         _conf_libvirtd = get_vars.get("libvirt_libvirtd", {})
#         _conf_libvirtd_tcp_port = _conf_libvirtd.get("tcp_port", None)
#
#         if not _conf_libvirtd_tcp_port:
#             assert False, "TCP is enabled, but no port ist configured"
#
#         log_outputs = (
#             'log_outputs               = "2:file:/var/log/libvirt/libvirtd.log 3:journald"'
#         )
#         listen_tcp = "listen_tcp                = 1"
#         listen_tcp_port = f'tcp_port                  = "{_conf_libvirtd_tcp_port}"'
#
#         config_file = host.file("/etc/libvirt/libvirtd.conf")
#
#         assert config_file.is_file
#
#         assert log_outputs in config_file.content_string
#         assert listen_tcp in config_file.content_string
#         assert listen_tcp_port in config_file.content_string
#     else:
#
#         _conf_daemons = get_vars.get("libvirt_services", {})
#
#         print(pp_json(_conf_daemons))
#
#         _conf_daemon_socket = _conf_daemons.get("socket", {})
#
#         if _conf_daemon_socket.get("enabled", True):
#             """" virtproxy used """
#             config_file = host.file("/etc/libvirt/virtproxyd.conf")
#             content = config_file.content_string.split("\n")
#
#             listen_addr = 'listen_addr.* = "192.168.0.1"'
#             log_outputs = 'log_outputs.* = "3:syslog:virtproxyd'
#
#             reg_listen_addr = re.compile(listen_addr)
#             reg_log_outputs = re.compile(log_outputs)
#
#             assert len(list(filter(reg_listen_addr.match, content))) > 0
#             assert len(list(filter(reg_log_outputs.match, content))) > 0


#        assert True == False

def test_service_running_and_enabled(host, get_vars):
    """
    Forced monolithic model (libvirt_daemon_model: monolithic): even on a
    libvirt >= 10 host the monolithic libvirtd must run, while the modular
    driver daemons must be disabled. virtlogd / virtlockd stay enabled, since
    libvirtd relies on them.
    """
    _facts = local_facts(host=host, fact="libvirtd")
    _version = _facts.get('version')

    print(f"installed version: {_version}")

    # the monolithic daemon must be up regardless of the libvirt version
    libvirtd = host.service("libvirtd")
    assert libvirtd.is_running, "libvirtd.service must be running"
    assert libvirtd.is_enabled, "libvirtd.service must be enabled"

    # the modular driver daemons must be disabled when monolithic is forced
    for s in ["virtqemud.socket", "virtstoraged.socket"]:
        assert not host.service(s).is_enabled, \
            f"{s} must be disabled in monolithic mode"

# TODO
# def test_listening_socket(host, get_vars):
#     """ """
#     _version = version(host)
#
#     print(f"installed version: {_version}")
#     listen = []
#
#     listening = host.socket.get_listening_sockets()
#
#     for i in listening:
#         print(i)
#
#     if Version(_version) > Version("10.0"):
#
#         _conf_libvirtd = get_vars.get("libvirt_libvirtd", {})
#         _conf_libvirtd_tcp = _conf_libvirtd.get("enable_tcp", True)
#
#         if _conf_libvirtd_tcp:
#             _conf_libvirtd_tcp_port = _conf_libvirtd.get("tcp_port", None)
#
#             if not _conf_libvirtd_tcp_port:
#                 assert False, "TCP is enabled, but no port ist configured"
#
#             listen.append(f"tcp://0.0.0.0:{_conf_libvirtd_tcp_port}")
#
#     for spec in listen:
#         socket = host.socket(spec)
#         assert socket.is_listening
