# Ansible Role - bodsch.kvm.instances

Create and run **KVM instances (VMs)** by cloning the base images provisioned by
`bodsch.kvm.base_images`.

Per instance the role:

1. clones the OS disk and creates any data disks —
   [`bodsch.kvm.libvirt_volume`](../../plugins/modules/libvirt_volume.py);
2. builds a cloud-init NoCloud seed ISO from the rendered user-data /
   meta-data / network-config —
   [`bodsch.kvm.libvirt_cloud_init_iso`](../../plugins/modules/libvirt_cloud_init_iso.py);
3. defines the domain from structured parameters and reconciles its run state —
   [`bodsch.kvm.libvirt_domain`](../../plugins/modules/libvirt_domain.py).

There is no `community.libvirt` and no `vm.xml.j2` template anymore — the domain
XML is built and validated by the module. The pool path and the
`kvm`/`qemu` domain type are detected automatically (`prepare.yml`).

## Requirements

* A storage pool (`bodsch.kvm.storage_pool`), a virtual network
  (`bodsch.kvm.network`, `state: active`) and base images
  (`bodsch.kvm.base_images`) must already exist.
* `libvirt-python`, `pycdlib` (installed by `prepare.yml`) and `PyYAML` on the host.

## Role variables

| Variable | Default | Description |
| :-- | :-- | :-- |
| `instances_libvirt.uri` | `qemu:///system` | libvirt connection URI |
| `instances_libvirt.pool` | `default` | storage pool (= a `storage_pools[].name`) |
| `instances_libvirt.network` | `vm-network` | virtual network (= a `virtual_networks[].name`, `active`) |
| `instances_os_base_volumes` | `{}` | map of `os` → base volume name (= a `base_images[].dest`) |
| `instances_autostart` | `true` | start domains on host boot |
| `instances_state` | `running` | default run state for instances without their own `state` |
| `instances_graphics.type` | `spice` | `spice`, `vnc`, or `none`/`""` for a headless domain |
| `instances_ssh_public_key` | `""` | public key injected via cloud-init |
| `instances` | `[]` | list of VMs (see below) |

Device mapping (in `vars/`): `instances_root_disk_bus` (`virtio`),
`instances_cdrom_bus` (`sata`), `instances_data_disk_letters`.

Each item of `instances`:

| Key | Required | Description |
| :-- | :-- | :-- |
| `hostname` | yes | guest hostname; also the libvirt domain name |
| `name` | no | override the domain name (default: `hostname`) |
| `os` | yes | selects `cloud_init_<os>.yaml.j2` and `instances_os_base_volumes[<os>]` |
| `vcpus`, `memory_mb`, `os_disk_gb` | yes | sizing |
| `data_disks` | no | list of `{ name, size_gb }` (become `vdb`, `vdc`, …) |
| `ip` | yes | `{ prefix, octet }` → static address `prefix.octet/24` |
| `state` | no (`instances_state`) | see run-state table below |

The domain is always defined first; `state` then reconciles its run state on
every run:

| `state`     | effect                                                        |
|-------------|---------------------------------------------------------------|
| `running`   | start (or unpause) the domain                                 |
| `defined`   | only define it; leave the current run state untouched         |
| `shutdown`  | graceful ACPI shutdown (stops a running domain)               |
| `destroyed` | forced power-off                                              |
| `paused`    | pause (only takes effect if the domain is currently running)  |

## Example

```yaml
- hosts: kvm_hosts
  become: true
  roles:
    - role: bodsch.kvm.instances
  vars:
    instances_libvirt:
      uri: "qemu:///system"
      pool: "pool"                       # = storage_pools[].name
      network: "vm-network"              # = virtual_networks[].name
    instances_ssh_public_key: "ssh-ed25519 AAAA..."
    instances_os_base_volumes:
      debian: "debian-12-base.qcow2"     # = base_images[].dest
    instances:
      - hostname: dns
        os: debian
        vcpus: 1
        memory_mb: 1024
        os_disk_gb: 10
        data_disks:
          - { name: data0, size_gb: 20 }
        ip: { prefix: "192.168.0", octet: 11 }
        # state: running
      - hostname: build
        os: debian
        vcpus: 2
        memory_mb: 2048
        os_disk_gb: 20
        ip: { prefix: "192.168.0", octet: 12 }
        state: defined                   # only define, do not start
```

## License

[Apache](../../LICENSE)
