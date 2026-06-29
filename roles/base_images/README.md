# Ansible Role - bodsch.kvm.base_images

Download **base / cloud images** (qcow2) into a libvirt storage pool, ready to be
cloned by the `bodsch.kvm.instances` role.

The role consumes a pool that already exists (created by
`bodsch.kvm.storage_pool`). It uses the native
[`bodsch.kvm.libvirt_pool`](../../plugins/modules/libvirt_pool.py) module (no
`community.libvirt`) to ensure the pool is active and to read its target path
directly as a fact — the previous `get_xml` + XML parsing is gone. After
downloading, the pool is refreshed so libvirt registers the new volumes.

## Requirements

* A storage pool provisioned by `bodsch.kvm.storage_pool`.
* `libvirt-python` on the managed host.

## Role variables

| Variable | Default | Description |
| :-- | :-- | :-- |
| `base_images_libvirt.uri` | `qemu:///system` | libvirt connection URI |
| `base_images_libvirt.pool` | `default` | pool to import into (must be a `storage_pools[].name`) |
| `base_images` | `[]` | list of images to download (see below) |

Each item of `base_images`:

| Key | Required | Description |
| :-- | :-- | :-- |
| `source` | yes | URL of the qcow2 image |
| `dest` | yes | volume file name inside the pool (referenced by `instances_os_base_volumes[<os>]`) |
| `checksum` | no | checksum for `get_url`, e.g. `sha256:<hash>` or `sha256:<url>` |

## Example

```yaml
- hosts: kvm_hosts
  become: true
  roles:
    - role: bodsch.kvm.base_images
  vars:
    base_images_libvirt:
      uri: "qemu:///system"
      pool: "pool"                       # = storage_pools[].name
    base_images:
      - source: "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2"
        dest: "debian-12-base.qcow2"
        checksum: "sha512:https://cloud.debian.org/images/cloud/bookworm/latest/SHA512SUMS"
```

The volume is then available to `instances` via:

```yaml
instances_os_base_volumes:
  debian: "debian-12-base.qcow2"         # = base_images[].dest
```

## License

[Apache](../../LICENSE)
