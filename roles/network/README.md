# Ansible Role - bodsch.kvm.network

Manage libvirt **virtual networks** on a KVM host.

The networks are reconciled with the native
[`bodsch.kvm.libvirt_network`](../../plugins/modules/libvirt_network.py) module
(no `community.libvirt`). The role keeps its flat, familiar data model
(`enable_dhcp` / `dhcp_*` plus the network-level domain/DNS variables); the
`bodsch.kvm.network_specs` filter translates it into the module's structured
`dns` / `dhcp` / `vlans` parameters, which are validated (IPv4 addresses,
netmask, VLAN tags) before the XML is built.

## Requirements

* libvirt installed and its daemons running (use the `bodsch.kvm.libvirt` role first).
* `libvirt-python` on the managed host.

## Role variables

| Variable | Default | Description |
| :-- | :-- | :-- |
| `virtual_networks` | `[]` | list of networks to manage (see below) |
| `network_domain_name` | `""` | DNS domain announced for DHCP-enabled networks |
| `network_dns_primary` | `""` | primary DNS forwarder (DHCP-enabled networks) |
| `network_dns_secondary` | `""` | secondary DNS forwarder (DHCP-enabled networks) |

Each item of `virtual_networks`:

| Key | Required | Description |
| :-- | :-- | :-- |
| `name` | yes | network name |
| `mode` | no | `nat`, `route`, `bridge` or `private` (isolated) |
| `bridge_name` | with `mode` | bridge device name |
| `route_device` | with `mode: route` | host device to route through |
| `state` | no (`present`) | `present`, `active`, `inactive`, `absent` |
| `autostart` | no | start the network on host boot |
| `enable_dhcp` | no | enable the IPv4 DHCP block below |
| `dhcp_gateway` / `dhcp_netmask` | with DHCP | network address + mask |
| `dhcp_scope_start` / `dhcp_scope_end` | with DHCP | DHCP range |
| `virtualport_type` | no | e.g. `openvswitch` |
| `vlan` | no | network-wide VLAN tag |
| `vlans` | no | VLAN portgroups: `{ name, default, trunk, vlan }` (`vlan` is one id, or a list when `trunk: true`) |

## Example

```yaml
- hosts: kvm_hosts
  become: true
  roles:
    - role: bodsch.kvm.network
  vars:
    network_domain_name: "example.lan"
    network_dns_primary: "192.168.0.1"
    network_dns_secondary: "1.1.1.1"
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
```

## License

[Apache](../../LICENSE)
