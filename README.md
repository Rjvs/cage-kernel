# Cage Kernel

## Purpose And Criticality

`cage-kernel` is the reproducible build unit for the macOS ContainerKit guest
kernel used by Cage live direct-volume attach.

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
```

`prepare` creates or refreshes `.local/cage-kernel/containerization`, checks out
the pinned upstream revision, resets that managed checkout, and applies the
hotplug guest patch.

`build` runs `prepare`, then runs `make` in the upstream `kernel/` directory and
verifies the resulting `.local/cage-kernel/containerization/kernel/vmlinux`.

`install-local` copies the verified kernel to
`app/isolate/cage/.local/vmlinux`, the source-checkout location Cage probes
before falling back to the Apple `container` CLI kernel cache.

`acceptance` builds, installs, and runs the focused macOS live direct-volume
integration test with `CAGE_TEST_KERNEL_PATH` set to the installed kernel.

## Compatibility Notes

This unit is consumed by Cage on macOS only. It does not change the Cage public
API and does not affect Windows/HCS.

The patch is intentionally kernel-config-only. No Swift source edits to
`apple/containerization` are required for Cage's current direct live-attach
path; those belong to separate pod/shared-volume investigations.

## Release Pointer

Releases are tagged as `cage-kernel/v{version}`. A release should record the
upstream Containerization revision, the guest kernel version built by upstream's
`kernel/Makefile`, and the live-volume acceptance result.
