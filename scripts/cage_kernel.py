#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Build and verify the Cage ContainerKit guest kernel."""

from __future__ import annotations

import argparse
import compileall
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

UNIT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = UNIT_ROOT.parents[2]
DEFAULT_WORK_DIR = REPO_ROOT / ".local" / "cage-kernel"
DEFAULT_CONTAINERIZATION_URL = "https://github.com/apple/containerization.git"
DEFAULT_CONTAINERIZATION_REVISION = "25558e6b85251104b13d9ae91b5721c071052047"
PATCH_PATH = UNIT_ROOT / "patches" / "containerization-hotplug-guest.patch"
DEFAULT_INSTALL_PATH = REPO_ROOT / "app" / "isolate" / "cage" / ".local" / "vmlinux"
LIVE_VOLUME_INTEGRATION_TEST = (
    "tests/integration/test_containerkit_live_volumes.py::"
    "TestContainerKitLiveVolumes::test_direct_ext4_volume_live_attach_persists"
)
REQUIRED_CONFIG_LINES = frozenset(
    {
        "CONFIG_SCSI=y",
        "CONFIG_BLK_DEV_SD=y",
        "CONFIG_USB=y",
        "CONFIG_USB_XHCI_HCD=y",
        "CONFIG_USB_STORAGE=y",
        "CONFIG_USB_UAS=y",
    }
)


def repo_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def run(
    argv: list[str],
    *,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    display = " ".join(argv)
    print(f"+ {display}", flush=True)
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=capture,
        check=True,
    )


def managed_checkout(args: argparse.Namespace) -> Path:
    return args.work_dir.resolve() / "containerization"


def built_kernel_path(args: argparse.Namespace) -> Path:
    return managed_checkout(args) / "kernel" / "vmlinux"


def ensure_safe_work_dir(work_dir: Path) -> None:
    resolved = work_dir.resolve(strict=False)
    allowed_root = (REPO_ROOT / ".local").resolve()
    if resolved != allowed_root and allowed_root not in resolved.parents:
        raise SystemExit(
            f"refusing to manage checkout outside repo .local/: {repo_path(resolved)}"
        )


def checkout_revision(checkout: Path, revision: str) -> None:
    try:
        run(["git", "checkout", "--detach", revision], cwd=checkout)
    except subprocess.CalledProcessError:
        run(["git", "fetch", "origin", revision], cwd=checkout)
        run(["git", "checkout", "--detach", revision], cwd=checkout)


def apply_hotplug_patch(checkout: Path) -> None:
    run(["git", "apply", "--check", str(PATCH_PATH)], cwd=checkout)
    run(["git", "apply", str(PATCH_PATH)], cwd=checkout)


def prepare(args: argparse.Namespace) -> int:
    ensure_safe_work_dir(args.work_dir)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    checkout = managed_checkout(args)

    if (checkout / ".git").is_dir():
        run(["git", "fetch", "--tags", "origin"], cwd=checkout)
    else:
        run(
            [
                "git",
                "clone",
                "--no-checkout",
                args.containerization_url,
                str(checkout),
            ],
            cwd=REPO_ROOT,
        )

    checkout_revision(checkout, args.containerization_revision)
    run(["git", "reset", "--hard", args.containerization_revision], cwd=checkout)
    run(["git", "clean", "-fdx"], cwd=checkout)
    apply_hotplug_patch(checkout)
    print(f"Prepared {repo_path(checkout)} at {args.containerization_revision}")
    return 0


def read_kernel_config(kernel: str | Path) -> str | None:
    try:
        data = Path(kernel).read_bytes()
    except OSError:
        return None

    start = data.find(b"IKCFG_ST")
    if start >= 0:
        start += len(b"IKCFG_ST")
        end = data.find(b"IKCFG_ED", start)
        if end >= 0:
            config = data[start:end]
            if config.startswith(b"\x1f\x8b\x08"):
                try:
                    config = zlib.decompress(config, 16 + zlib.MAX_WBITS)
                except zlib.error:
                    return None
            return config.decode(errors="replace")

    for match in re.finditer(b"\x1f\x8b\x08", data):
        try:
            config = zlib.decompress(data[match.start() :], 16 + zlib.MAX_WBITS)
        except zlib.error:
            continue
        if config.startswith(b"#") and b"CONFIG_" in config:
            return config.decode(errors="replace")
    return None


def kernel_config_lines(kernel: Path) -> set[str]:
    config = read_kernel_config(kernel)
    if config is None:
        raise SystemExit(f"{repo_path(kernel)} does not contain an embedded kernel config")
    return set(config.splitlines())


def verify_kernel(kernel: Path) -> None:
    if not kernel.is_file():
        raise SystemExit(f"kernel image not found: {repo_path(kernel)}")
    options = kernel_config_lines(kernel)
    missing = sorted(REQUIRED_CONFIG_LINES - options)
    if missing:
        rendered = ", ".join(missing)
        raise SystemExit(f"{repo_path(kernel)} is missing required config: {rendered}")
    print(f"{repo_path(kernel)} supports Cage live volume attach")


def verify(args: argparse.Namespace) -> int:
    kernel = args.kernel if args.kernel is not None else built_kernel_path(args)
    verify_kernel(kernel.resolve(strict=False))
    return 0


def build(args: argparse.Namespace) -> int:
    if shutil.which("container") is None:
        raise SystemExit(
            "`container` CLI is required to build apple/containerization/kernel"
        )
    if not args.no_prepare:
        prepare(args)
    run(["make"], cwd=managed_checkout(args) / "kernel")
    verify_kernel(built_kernel_path(args))
    return 0


def install_local(args: argparse.Namespace) -> int:
    source = args.kernel if args.kernel is not None else built_kernel_path(args)
    verify_kernel(source)
    destination = args.install_path.resolve(strict=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"Installed {repo_path(source)} to {repo_path(destination)}")
    return 0


def acceptance(args: argparse.Namespace) -> int:
    build(args)
    install_args = argparse.Namespace(**vars(args))
    install_args.kernel = built_kernel_path(args)
    install_local(install_args)
    env = os.environ.copy()
    env["CAGE_TEST_KERNEL_PATH"] = str(args.install_path.resolve(strict=False))
    run(
        [
            "./tools/repo/run",
            "cage",
            "test-integration-macos",
            LIVE_VOLUME_INTEGRATION_TEST,
        ],
        env=env,
    )
    return 0


def validate_patch_file() -> None:
    text = PATCH_PATH.read_text(encoding="utf-8")
    missing = sorted(line for line in REQUIRED_CONFIG_LINES if line not in text)
    if missing:
        rendered = ", ".join(missing)
        raise SystemExit(f"{repo_path(PATCH_PATH)} is missing required lines: {rendered}")
    if "Sources/Containerization" in text or "Sources/" in text:
        raise SystemExit(f"{repo_path(PATCH_PATH)} must be a kernel/config-arm64 patch only")


def self_test() -> int:
    validate_patch_file()
    config = "\n".join(["# CONFIG_TEST=y", *sorted(REQUIRED_CONFIG_LINES), ""]) + "\n"
    plain = b"prefix IKCFG_ST" + config.encode() + b"IKCFG_ED suffix"
    compressed = b"prefix IKCFG_ST" + gzip.compress(config.encode()) + b"IKCFG_ED suffix"
    stream = b"prefix" + gzip.compress(config.encode()) + b"suffix"
    with tempfile.TemporaryDirectory(prefix="cage-kernel-test-") as directory:
        tmp = Path(directory) / "vmlinux"
        for payload in (plain, compressed, stream):
            tmp.write_bytes(payload)
            found = read_kernel_config(tmp)
            if found is None or not REQUIRED_CONFIG_LINES <= set(found.splitlines()):
                raise AssertionError("failed to extract synthetic kernel config")
    print("cage-kernel self-test passed")
    return 0


def compile_script() -> None:
    if not compileall.compile_file(__file__, quiet=1, force=True):
        raise SystemExit(f"failed to compile {repo_path(Path(__file__))}")


def lint(_: argparse.Namespace) -> int:
    validate_patch_file()
    compile_script()
    print("cage-kernel lint passed")
    return 0


def typecheck(_: argparse.Namespace) -> int:
    compile_script()
    print("cage-kernel typecheck passed")
    return 0


def format_code(_: argparse.Namespace) -> int:
    print("cage-kernel has no formatter")
    return 0


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help="managed checkout directory, default: .local/cage-kernel",
    )
    parser.add_argument(
        "--containerization-url",
        default=DEFAULT_CONTAINERIZATION_URL,
        help="upstream apple/containerization Git URL",
    )
    parser.add_argument(
        "--containerization-revision",
        default=DEFAULT_CONTAINERIZATION_REVISION,
        help="upstream apple/containerization revision to build",
    )
    parser.add_argument(
        "--install-path",
        type=Path,
        default=DEFAULT_INSTALL_PATH,
        help="local Cage kernel install path",
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

    prepare_command = subparsers.add_parser("prepare")
    add_common_options(prepare_command)
    prepare_command.set_defaults(handler=prepare)

    for name, handler in (("build", build), ("acceptance", acceptance)):
        command = subparsers.add_parser(name)
        add_common_options(command)
        command.add_argument(
            "--no-prepare",
            action="store_true",
            help="reuse the existing prepared checkout",
        )
        command.set_defaults(handler=handler)

    verify_command = subparsers.add_parser("verify")
    add_common_options(verify_command)
    verify_command.add_argument("--kernel", type=Path, help="kernel image to verify")
    verify_command.set_defaults(handler=verify)

    install_command = subparsers.add_parser("install-local")
    add_common_options(install_command)
    install_command.add_argument("--kernel", type=Path, help="kernel image to install")
    install_command.set_defaults(handler=install_local)

    simple_handlers = {
        "format": format_code,
        "lint": lint,
        "typecheck": typecheck,
        "test": lambda _: self_test(),
    }
    for name, handler in simple_handlers.items():
        command = subparsers.add_parser(name)
        command.set_defaults(handler=handler)

    return root


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv[1:])
    try:
        return int(args.handler(args) or 0)
    except subprocess.CalledProcessError as exc:
        print(
            f"command failed with exit code {exc.returncode}: {' '.join(exc.cmd)}",
            file=sys.stderr,
        )
        return int(exc.returncode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
