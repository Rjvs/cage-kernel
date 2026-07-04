# Changelog

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
