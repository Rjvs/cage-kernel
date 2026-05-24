# Changelog

## 0.1.0

- Add a reproducible Cage ContainerKit guest-kernel build unit for live direct
  volume attach. The unit fetches upstream `apple/containerization`, applies the
  hotplug storage config patch, builds `kernel/vmlinux`, verifies the embedded
  config, and can install the result for local Cage integration runs.
