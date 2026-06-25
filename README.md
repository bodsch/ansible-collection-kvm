# Ansible Collection - bodsch.kvm

Documentation for the collection.


## supported Operating systems

Tested on

* ArchLinux
* Debian based
    - Debian 10 / 11 / 12
    - Ubuntu 20.04 / 22.04

> **RedHat-based systems are no longer officially supported! May work, but does not have to.**


## Requirements & Dependencies



## Included content


The collection provides one role per concern. They are designed to be combined
in a fixed order — see [Using this collection](#using-this-collection).

| Role | Description |
| :-- | :-- |
| [bodsch.kvm.libvirt](./roles/libvirt) | install libvirt and configure its daemons (monolithic `libvirtd` or modular `virt*d`) |
| [bodsch.kvm.storage_pool](./roles/storage_pool) | manage libvirt storage pools |
| [bodsch.kvm.network](./roles/network) | manage libvirt virtual networks |
| [bodsch.kvm.base_images](./roles/base_images) | download base / cloud images (qcow2) into a storage pool |
| [bodsch.kvm.instances](./roles/instances) | create and run KVM instances (VMs) from the base images |


### Modules

| Name | Description |
| :-- | :-- |
| `bodsch.kvm.libvirtd_version` | detect the installed libvirtd version |
| `bodsch.kvm.modular_services` | manage the modular libvirt daemons (`virt*d`) via systemd |
| `bodsch.kvm.monolithic_services` | manage the monolithic `libvirtd` via systemd |


## Installing this collection

You can install the memsource collection with the Ansible Galaxy CLI:

```bash
ansible-galaxy collection install bodsch.kvm
```

To install directly from GitHub:

```bash
ansible-galaxy collection install git@github.com:bodsch/ansible-collection-kvm.git
```


You can also include it in a `requirements.yml` file and install it with `ansible-galaxy collection install -r requirements.yml`, using the format:

```yaml
---
collections:
  - name: bodsch.kvm
```

The python module dependencies are not installed by `ansible-galaxy`.  They can
be manually installed using pip:

```bash
pip install -r requirements.txt
```

## Using this collection

The collection splits a KVM host into one role per concern. The roles are
*consume-only* — each assumes the previous ones already ran — so they must be
applied in this order:

```text
libvirt → storage_pool → network → base_images → instances
```

* **libvirt** — installs libvirt and configures its daemons. From libvirt 10 it
  uses the modular `virt*d` daemons, below 10 the monolithic `libvirtd`. Override
  with `libvirt_daemon_model: auto | monolithic | modular`. It publishes the
  resolved model as the `ansible_local.libvirtd` fact, which the other roles read.
* **storage_pool** — defines libvirt storage pools from `storage_pools`.
* **network** — defines libvirt virtual networks from `virtual_networks`.
* **base_images** — downloads qcow2 base / cloud images into a pool (`base_images`).
* **instances** — clones the base images and creates the VMs (`instances`).

### Variable contracts between the roles

These names must line up across roles, otherwise VM creation fails late:

| this … | … must match … |
| :-- | :-- |
| `instances_libvirt.pool`, `base_images_libvirt.pool` | a `storage_pools[].name` |
| `instances_libvirt.network` | a `virtual_networks[].name` (use `state: active` so VMs can start) |
| `instances_os_base_volumes[<os>]` | a `base_images[].dest` |
| an instance's `os` | a `cloud_init_<os>.yaml.j2` template (ships `arch`, `debian`) |

### Example

A playbook that wires the whole chain:

```yaml
---
- name: kvm host
  hosts: kvm_hosts
  become: true

  roles:
    - role: bodsch.kvm.libvirt
    - role: bodsch.kvm.storage_pool
    - role: bodsch.kvm.network
    - role: bodsch.kvm.base_images
    - role: bodsch.kvm.instances
```

with matching variables (e.g. in `group_vars`):

```yaml
---
# libvirt daemon model (optional; default: auto)
libvirt_daemon_model: auto

# storage_pool
storage_pools:
  - name: pool
    path: /var/lib/libvirt/pool
    state: active
    autostart: true

# network
virtual_networks:
  - name: vm-network
    mode: nat
    bridge_name: virbr-vm
    state: active
    autostart: true
    enable_dhcp: true
    dhcp_gateway: "192.168.0.1"
    dhcp_netmask: "255.255.255.0"
    dhcp_scope_start: "192.168.0.2"
    dhcp_scope_end: "192.168.0.254"
network_domain_name: "example.lan"
network_dns_primary: "192.168.0.1"
network_dns_secondary: "1.1.1.1"

# base_images (downloaded into the pool above; dest == the volume name)
base_images:
  - source: "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2"
    dest: "debian-12-base.qcow2"

# instances
instances_libvirt:
  uri: "qemu:///system"
  pool: "pool"               # = storage_pools[].name
  network: "vm-network"      # = virtual_networks[].name
instances_ssh_public_key: "ssh-ed25519 AAAA..."
instances_os_base_volumes:
  debian: "debian-12-base.qcow2"   # = base_images[].dest
instances:
  - hostname: dns
    os: debian                     # → cloud_init_debian.yaml.j2
    vcpus: 1
    memory_mb: 1024
    os_disk_gb: 10
    data_disks:
      - { name: data0, size_gb: 20 }
    ip: { prefix: "192.168.0", octet: 11 }
    # state: running               # running | defined | shutdown | destroyed | paused
```

`instances` is a list; each entry needs a unique `hostname` (also used as the
libvirt domain name, override with `name`). The domain is always defined first,
then `state` reconciles its run state on every run (default `running`,
configurable via `instances_state`):

| `state`     | effect                                                        |
|-------------|---------------------------------------------------------------|
| `running`   | start (or unpause) the domain                                 |
| `defined`   | only define it; leave the current run state untouched         |
| `shutdown`  | graceful ACPI shutdown (stops a running domain)               |
| `destroyed` | forced power-off                                              |
| `paused`    | pause (only takes effect if the domain is currently running)  |

## Contribution

Please read [Contribution](CONTRIBUTING.md)

## Development,  Branches (Git Tags)

The `master` Branch is my *Working Horse* includes the "latest, hot shit" and can be complete broken!

If you want to use something stable, please use a [Tagged Version](https://github.com/bodsch/ansible-collection-kvm/tags)!


## Author

- Bodo Schulz

## License

[Apache](LICENSE)

**FREE SOFTWARE, HELL YEAH!**
