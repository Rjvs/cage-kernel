# Changelog

## 0.2.0

- Add the Containerization #681 CIFS kernel options to the Cage guest config
  patch and verification requirements so macOS guests can mount pod-owned
  Samba shares through CIFS.

## 0.1.0

- Add a reproducible Cage ContainerKit guest-kernel build unit for live direct
  volume attach. The unit fetches upstream `apple/containerization`, applies the
  hotplug storage config patch, builds `kernel/vmlinux`, verifies the embedded
  config, and can install the result for local Cage integration runs.
