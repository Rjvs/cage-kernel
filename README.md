# Cage Kernel

## Purpose And Criticality

`cage-kernel` is the reproducible build unit for the macOS ContainerKit guest
kernel used by Cage live direct-volume attach. Public release artifacts are
published from [`Rjvs/cage-kernel`](https://github.com/Rjvs/cage-kernel); this
monorepo copy remains the local development and compatibility reference.

Cage can hotplug a direct ext4 volume into a running ContainerKit VM only when
the guest kernel has SCSI disk, XHCI, USB mass storage, and UAS support. The
current upstream `apple/containerization` framework has the host-side NBD and
hotplug API surface Cage needs, but its guest kernel config still needs this
storage-driver patch until the options land upstream.

## What This Unit Ships

- `patches/containerization-hotplug-guest.patch`: the minimal
  `kernel/config-arm64` patch for the Containerization guest.
- `scripts/cage_kernel.py`: a managed workflow to fetch upstream
  `apple/containerization`, apply the patch, build `kernel/vmlinux`, verify the
  embedded kernel config, install it for Cage, and run the focused live-volume
  acceptance test.
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
    containerization-hotplug-guest.patch
  scripts/
    cage_kernel.py
```

Generated checkouts and build products are written under
`.local/cage-kernel/`, which is ignored by git.

## Development Commands

```bash
./tools/repo/run cage-kernel prepare
./tools/repo/run cage-kernel build
./tools/repo/run cage-kernel verify
./tools/repo/run cage-kernel install-local
./tools/repo/run cage-kernel acceptance
./tools/repo/run --raw cage-kernel diagnose-dns
```

`prepare` creates or refreshes `.local/cage-kernel/containerization`, checks out
the pinned upstream revision, resets that managed checkout, and applies the
hotplug guest patch.

`build` runs `prepare`, then performs the same steps as the upstream
`kernel/Makefile`: build the `kernel-build:0.1` image, download
`source.tar.xz` from kernel.org when missing, run `build.sh` in the build
container, and verify the resulting
`.local/cage-kernel/containerization/kernel/vmlinux`.

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
./tools/repo/run --raw cage-kernel build --dns 10.2.1.1
./tools/repo/run --raw cage-kernel acceptance --dns 10.2.1.1
```

`diagnose-dns` prints the discovered host DNS servers, Apple `container`
service and builder status, and compares default container DNS with explicit
host DNS:

```bash
./tools/repo/run --raw cage-kernel diagnose-dns
./tools/repo/run --raw cage-kernel diagnose-dns --dns 10.2.1.1
```

`install-local` copies the verified kernel to
`app/isolate/cage/.local/vmlinux`, the source-checkout location Cage probes
before the managed public-release cache.

`acceptance` builds, installs, and runs the focused macOS live direct-volume
integration test with `CAGE_TEST_KERNEL_PATH` set to the installed kernel.

## Compatibility Notes

This unit is consumed by Cage on macOS only. It does not change the Cage public
API and does not affect Windows/HCS.

The patch is intentionally kernel-config-only. No Swift source edits to
`apple/containerization` are required for Cage's current direct live-attach
path; those belong to separate pod/shared-volume investigations.

## Release Pointer

Public releases are tagged in `Rjvs/cage-kernel` as `v{version}` and publish
`vmlinux.zst`, `manifest.json`, and `SHA256SUMS`. The manifest records the
upstream Containerization revision, Linux source version, patch hash, artifact
hashes, and live-volume acceptance result.
