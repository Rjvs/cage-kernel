# Cage Kernel

`cage-kernel` builds and publishes the macOS ContainerKit guest kernel used by
Cage live direct-volume attach.

Cage needs a guest kernel with SCSI disk, XHCI, USB mass storage, and UAS
support so a hotplugged direct ext4 volume appears inside the VM. The upstream
Apple Containerization framework has the host-side hotplug surface Cage needs,
but the guest kernel config still needs this storage-driver patch until the
options land upstream.

## Release Artifacts

GitHub Releases are the distribution channel. Each release publishes:

- `vmlinux.zst` — zstd-compressed guest kernel.
- `manifest.json` — build provenance, source revisions, hashes, and acceptance
  status.
- `SHA256SUMS` — checksums for `manifest.json` and `vmlinux.zst`.

Consumers must verify `SHA256SUMS`, verify the artifact hashes in
`manifest.json`, decompress to a local `vmlinux` path, and verify the embedded
kernel config before passing the path to ContainerKit.

## Requirements

- macOS on Apple silicon.
- Xcode command line tools.
- Apple `container` CLI on `PATH`.
- `zstd` on `PATH` for packaging.
- Network access to clone `https://github.com/apple/containerization.git` and
  download the Linux kernel source.

The default upstream revision is
`25558e6b85251104b13d9ae91b5721c071052047`, matching Oja/Cage's current
Containerization SwiftPM pin.

## Commands

```bash
uv run --script scripts/cage_kernel.py prepare
uv run --script scripts/cage_kernel.py build
uv run --script scripts/cage_kernel.py verify
uv run --script scripts/cage_kernel.py package
```

`prepare` creates or refreshes `.local/cage-kernel/containerization`, checks out
the pinned upstream revision, resets that managed checkout, and applies
`patches/containerization-hotplug-guest.patch`.

`build` runs `prepare`, then follows upstream's `kernel/Makefile` flow to build
`.local/cage-kernel/containerization/kernel/vmlinux`.

`verify` checks the embedded kernel config for the required live-attach options.

`package` writes release artifacts to `dist/`.

If automatic DNS discovery is wrong for your network, pass explicit DNS
servers:

```bash
uv run --script scripts/cage_kernel.py build --dns 10.2.1.1
```

## Acceptance

Acceptance runs against an Oja/Cage monorepo checkout because the integration
test lives there:

```bash
uv run --script scripts/cage_kernel.py acceptance --cage-repo /path/to/oja
```

The command builds and installs the kernel locally, then runs:

```bash
./tools/repo/run cage test-integration-macos \
  tests/integration/test_containerkit_live_volumes.py::TestContainerKitLiveVolumes::test_direct_ext4_volume_live_attach_persists
```

## Release Flow

1. PRs run script lint/self-test and patch validation.
2. Tags matching `vX.Y.Z-rc.N` build and upload prerelease artifacts.
3. Private QA installs that exact prerelease artifact and runs acceptance.
4. The manual `Bless Release` workflow creates `vX.Y.Z` from the RC assets and
   checksums; it does not rebuild a different kernel.

## Compatibility

This repo publishes a macOS-only binary artifact. It does not ship a runnable
container image. Runtime consumers must materialize a local `vmlinux` file and
pass that file path to Containerization.
