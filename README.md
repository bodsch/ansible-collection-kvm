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


### Roles

| Role                                                                       | Build State | Description |
|:---------------------------------------------------------------------------| :---------: | :----       |
| [bodsch.lvm.libvirt](./roles/libvirt/README.md)                            | [![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/bodsch/ansible-collection-kvm/libvirt.yml?branch=main)][libvirt] | Ansible role to configure libvirt. |

[libvirt]: https://github.com/bodsch/ansible-collection-kvm/actions/workflows/libvirt.yml


### Modules

| Name                      | Description |
|:--------------------------|:----|
|                           |     |


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
