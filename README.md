# Cage Kernel

## Purpose And Criticality

`cage-kernel` is the reproducible build unit for macOS ContainerKit guest
kernels used by Cage. Public release artifacts are published from
[`Rjvs/cage-kernel`](https://github.com/Rjvs/cage-kernel); this monorepo copy
remains the local development and compatibility reference.

Cage can hotplug a direct ext4 volume into a running ContainerKit VM only when
the guest kernel has SCSI disk, XHCI, USB mass storage, and UAS support. Cage
can use guest-side NBD only when the kernel also has NBD support. Cage can
mount SMB/Samba shares inside the guest only when the kernel also has CIFS
support. The tool can create and publish three explicit profiles:

| Profile | Description |
|---------|-------------|
| `hotplug` | Vanilla pinned `apple/containerization` guest kernel plus Cage's hotplug direct-volume config. This is the default profile and the backward-compatible `vmlinux.zst` release asset. |
| `nbd` | `hotplug` plus guest-side NBD transport config. |
| `nbd-cifs` | `nbd` plus SMB/CIFS guest-mount config. |

## What This Unit Ships

- `patches/containerization-hotplug-guest.patch`: the minimal
  `kernel/config-arm64` patch for Cage hotplug direct-volume support.
- `patches/containerization-nbd-guest.patch`: the minimal
  `kernel/config-arm64` patch for Cage guest-side NBD transport support.
- `patches/containerization-cifs-guest.patch`: the optional CIFS config patch
  for upstream revisions that do not already carry the SMB/CIFS guest options.
- `scripts/cage_kernel.py`: a managed workflow to fetch upstream
  `apple/containerization`, apply profile patches, build `kernel/vmlinux`,
  verify the embedded kernel config, create profile artifacts, package release
  assets, publish them to `Rjvs/cage-kernel`, install them for Cage, and run the
  focused live-volume acceptance test.
- Unit metadata so the patch and workflow are visible through the normal repo
  commands.

## Dependencies

- macOS on Apple silicon.
- Xcode command line tools.
- The Apple `container` CLI on `PATH`.
- Network access to clone `https://github.com/apple/containerization.git`.
- Cage's integration-test prerequisites when running `acceptance`.

The default upstream revision is
`25558e6b85251104b13d9ae91b5721c071052047`, matching Cage's current
Containerization SwiftPM pin.

## Repo Structure

```text
app/isolate/cage-kernel/
  CHANGELOG.md
  VERSION
  patches/
    containerization-cifs-guest.patch
    containerization-hotplug-guest.patch
    containerization-nbd-guest.patch
  scripts/
    cage_kernel.py
```

Generated checkouts and build products are written under
`.local/cage-kernel/`, which is ignored by git.

## Development Commands

```bash
./tools/run cage-kernel prepare
./tools/run cage-kernel build
./tools/run cage-kernel create
./tools/run cage-kernel package-release
./tools/run cage-kernel publish
./tools/run cage-kernel verify
./tools/run cage-kernel install-local
./tools/run cage-kernel acceptance
./tools/run cage-kernel list-profiles
./tools/run --raw cage-kernel diagnose-dns
```

`prepare` creates or refreshes `.local/cage-kernel/containerization`, checks out
the pinned upstream revision, resets that managed checkout, and applies the
selected profile patches. Commands that operate on one kernel accept
`--profile hotplug`, `--profile nbd`, or `--profile nbd-cifs`; the default is
`hotplug`.

`build` runs `prepare`, then performs the same steps as the upstream
`kernel/Makefile`: build the `kernel-build:0.1` image, download
`source.tar.xz` from kernel.org when missing, run `build.sh` in the build
container, and verify the resulting
`.local/cage-kernel/containerization/kernel/vmlinux`. The verified result is
also copied to `.local/cage-kernel/kernels/<profile>/vmlinux`.

`create` builds every kernel profile by default:

```bash
./tools/run cage-kernel create
./tools/run cage-kernel create --profile hotplug --profile nbd --profile nbd-cifs
./tools/run cage-kernel create --install-local
```

`create --install-local` installs each profile for local Cage use. The default
`hotplug` profile is installed at `app/isolate/cage/.local/vmlinux` for
backwards compatibility. Other profiles install under
`app/isolate/cage/.local/kernels/<profile>/vmlinux`.

`package-release` packages existing profile artifacts from
`.local/cage-kernel/kernels/<profile>/vmlinux` into
`.local/cage-kernel/release/`:

```text
hotplug-vmlinux.zst
nbd-vmlinux.zst
nbd-cifs-vmlinux.zst
vmlinux.zst
manifest.json
SHA256SUMS
```

`vmlinux.zst` is a backward-compatible alias for `hotplug-vmlinux.zst`, so
current Cage release download code continues to consume the hotplug kernel. The
manifest records all three profiles and keeps the existing top-level
`artifacts.vmlinux` / `artifacts.vmlinux.zst` shape for that default hotplug
asset.

`publish` runs `package-release` and uploads the assets with GitHub CLI:

```bash
./tools/run cage-kernel publish
./tools/run cage-kernel publish -- --no-draft
./tools/run cage-kernel publish -- --tag v0.3.0 --repo Rjvs/cage-kernel
```

If the release tag already exists, `publish` uploads with `--clobber`. If it
does not exist, it creates a draft release by default.

On macOS, `build` discovers host DNS servers from `scutil --dns` and passes
them to both `container build` and `container run` with `--dns`. This avoids a
known Apple `container` failure mode where containers get `/etc/resolv.conf`
pointing at the default NAT gateway, such as `192.168.73.1`, but that resolver
cannot resolve `ports.ubuntu.com` for the Ubuntu package install in the build
image.

Some Apple `container` versions do not apply `container build --dns` to an
already-running BuildKit builder. When the image build fails, `cage-kernel`
falls back to a direct `ubuntu:focal` build container with the same package
recipe and explicit DNS, without stopping, deleting, or recreating the global
builder.

If automatic DNS discovery is wrong for your network, pass one or more explicit
DNS servers:

```bash
./tools/run --raw cage-kernel build --dns 10.2.1.1
./tools/run --raw cage-kernel acceptance --dns 10.2.1.1
```

`diagnose-dns` prints the discovered host DNS servers, Apple `container`
service and builder status, and compares default container DNS with explicit
host DNS:

```bash
./tools/run --raw cage-kernel diagnose-dns
./tools/run --raw cage-kernel diagnose-dns --dns 10.2.1.1
```

`install-local` copies the verified kernel to the profile's local Cage path.
For `hotplug`, that remains `app/isolate/cage/.local/vmlinux`, the
source-checkout location Cage probes before the managed public-release cache.

`acceptance` builds, installs, and runs the focused macOS live direct-volume
integration test with `CAGE_TEST_KERNEL_PATH` set to the installed kernel. It is
valid for all three profiles because each includes the hotplug storage config.

## Compatibility Notes

This unit is consumed by Cage on macOS only. It does not change the Cage public
API and does not affect Windows/HCS.

The patches are intentionally kernel-config-only. No Swift source edits to
`apple/containerization` are required for Cage's current direct live-attach
path; those belong to separate pod/shared-volume investigations.

## Release Pointer

Public releases are tagged in `Rjvs/cage-kernel` as `v{version}` and publish
the three profile artifacts, the backward-compatible `vmlinux.zst` hotplug
alias, `manifest.json`, and `SHA256SUMS`. The manifest records the upstream
Containerization revision, profile requirements, and artifact hashes.
