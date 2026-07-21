# Changelog

## 0.3.4

- Rebase all guest-kernel profiles on Apple Containerization 0.38.0 commit
  `d9868bb657fac3b55ed5dcec97c8eb8a08e78bf5` while retaining Cage's hotplug
  and NBD configuration deltas.
- Require every published profile to keep `CONFIG_VSOCKETS_LOOPBACK` unset;
  Containerization 0.38 already satisfies the optional CIFS profile settings.
- Consume 0.38's renamed `kernel/vmlinux-arm64` build output while preserving
  Cage's stable `vmlinux` profile and release asset names.
- Preserve validated kernel-source downloads outside the cleaned upstream
  checkout so building all three release profiles reuses one source archive.

## 0.3.3

- Make `publish` create full GitHub releases by default instead of draft
  releases, while retaining an explicit `--draft` option for staged releases.
- When publishing to an existing release, update the release draft state so a
  previous draft is published by a normal rerun.

## 0.3.2

- Resolve the default Linux kernel source from kernel.org release metadata so
  Cage tracks the latest non-EOL `6.18` source tarball instead of a stale point
  release URL.
- Download kernel sources with HTTP failure checks, validate cached
  `source.tar.xz` archives before reuse, and replace invalid cached responses
  before starting the build container.

## 0.3.1

- Fail fast when the Apple `container` system service is unavailable instead of
  reporting a DNS fallback and retrying another container command that cannot
  succeed.

## 0.3.0

- Add explicit Cage kernel profiles for the hotplug kernel that `Rjvs/cage-kernel`
  already publishes, the NBD plus hotplug kernel, and the NBD plus hotplug plus
  SMB/CIFS kernel.
- Add `create`, `package-release`, `publish`, and `list-profiles` commands so
  local workflows can build, package, publish, and install the full kernel range
  instead of one implicit patched kernel.
- Split the Containerization guest config patch into hotplug, NBD, and CIFS
  patches, and skip a profile patch when the pinned upstream revision already
  carries its required config.

## 0.2.0

- Add the Containerization #681 CIFS kernel options to the Cage guest config
  patch and verification requirements so macOS guests can mount SMB/Samba
  shares through CIFS.

## 0.1.0

- Add a reproducible Cage ContainerKit guest-kernel build unit for live direct
  volume attach. The unit fetches upstream `apple/containerization`, applies the
  hotplug storage config patch, builds `kernel/vmlinux`, verifies the embedded
  config, and can install the result for local Cage integration runs.
