# Ansible Role - bodsch.kvm.libvirt

Install libvirt and configure its daemons — either the **monolithic `libvirtd`**
or the **modular `virt*d`** daemons — and manage their systemd service/socket
lifecycle.

This is the **first** role in the collection; the others
(`storage_pool`, `network`, `base_images`, `instances`) assume it has run.

## What it does

1. **prepare** — validates `libvirt_daemon_model`.
2. **install** — installs the packages, detects the libvirtd version with
   [`bodsch.kvm.libvirtd_version`](../../plugins/modules/libvirtd_version.py),
   resolves the effective daemon model and publishes it as a local fact (below).
3. **configure** — renders the daemon configuration (`/etc/libvirt/*.conf`,
   drop-ins, and the sysconfig/`/etc/default` file) for the chosen model.
4. **service** — reconciles the units with
   [`bodsch.kvm.monolithic_services`](../../plugins/modules/monolithic_services.py)
   or [`bodsch.kvm.modular_services`](../../plugins/modules/modular_services.py).

### Daemon model

`libvirt_daemon_model` selects monolithic vs. modular:

| value | effect |
| :-- | :-- |
| `auto` (default) | monolithic below libvirt 10, modular from libvirt 10 onwards (version heuristic) |
| `monolithic` | always the monolithic `libvirtd` |
| `modular` | always the modular `virt*d` daemons |

The resolved model is published as the **`ansible_local.libvirtd`** fact so the
later roles do not re-detect it:

```yaml
ansible_local:
  libvirtd:
    version: "11.8.0"
    daemon_model: "auto"
    use_modular: true
```

## Role variables

| Variable | Default | Description |
| :-- | :-- | :-- |
| `libvirt_daemon_model` | `auto` | `auto` \| `monolithic` \| `modular` (see above) |
| `libvirt_services` | `{}` | per-daemon `service`/`socket` lifecycle (`state`, `enabled`); merged over `libvirt_defaults_services` |
| `libvirt_service` | `{}` | sysconfig / `/etc/default/libvirtd` settings (`libvirtd_args`, `qemu_audio_drv`, …) |

Per-daemon configuration dicts (each renders the matching daemon config file;
empty `{}` keeps the package default):

| Variable | Configures |
| :-- | :-- |
| `libvirt_libvirtd` | monolithic `libvirtd.conf` |
| `libvirt_qemu` | `qemu` / `virtqemud` |
| `libvirt_network` | `virtnetworkd` (e.g. `firewall_backend: iptables \| nftables`) |
| `libvirt_storage` | `virtstoraged` |
| `libvirt_secret` | `virtsecretd` |
| `libvirt_nodedev` | `virtnodedevd` |
| `libvirt_nwfilter` | `virtnwfilterd` |
| `libvirt_interface` | `virtinterfaced` |
| `libvirt_proxy` | `virtproxyd` |
| `libvirt_lock` | `virtlockd` / qemu lockd |
| `libvirt_log` | `virtlogd` |
| `libvirt_lxc` | `virtlxcd` / `lxc.conf` |
| `libvirt_ch` | `virtchd` |
| `libvirt_vbox` | `virtvboxd` |
| `libvirt_login_shell` | `virt-login-shell.conf` |

The `libvirt_services` keys mirror these daemons (`libvirtd`, `ch`, `interface`,
`lock`, `log`, `lxc`, `network`, `nodedev`, `nwfilter`, `proxy`, `qemu`,
`secret`, `storage`, `vbox`), each with a `service` and a `socket` block:

```yaml
libvirt_services:
  qemu:
    service: { state: stopped, enabled: false }
    socket:  { state: started, enabled: true }
```

## Example

Minimal — let libvirt pick the model and run with the package defaults:

```yaml
- hosts: kvm_hosts
  become: true
  roles:
    - role: bodsch.kvm.libvirt
```

Force the modular daemons and tweak a couple of settings:

```yaml
- hosts: kvm_hosts
  become: true
  roles:
    - role: bodsch.kvm.libvirt
  vars:
    libvirt_daemon_model: modular
    libvirt_network:
      firewall_backend: nftables
    libvirt_services:
      qemu:
        service: { state: stopped, enabled: false }
        socket:  { state: started, enabled: true }
      network:
        service: { state: stopped, enabled: false }
        socket:  { state: started, enabled: true }
```

## License

[Apache](../../LICENSE)
