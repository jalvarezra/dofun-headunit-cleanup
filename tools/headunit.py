#!/usr/bin/env python3
"""Inspect and clean up DoFun/TS-platform Android head units over ADB.

Standard library only. `check` never changes anything on the device.
"""
import argparse
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DISABLE_LIST = ROOT / "lists" / "disable.txt"
IOC_FILE = ROOT / "iocs" / "kaspersky-2026-08.json"
TWCORE_CACHE = "/sdcard/Android/data/com.tw.core/cache"
MD5_CHUNK = 25
EXIT_INDICATORS = 2


def find_adb():
    candidates = [
        os.environ.get("ADB"),
        shutil.which("adb"),
        str(Path.home() / "Library/Android/sdk/platform-tools/adb"),
        str(Path.home() / "Android/Sdk/platform-tools/adb"),
    ]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(str(Path(local) / "Android/Sdk/platform-tools/adb.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    sys.exit("adb not found. Install Android platform-tools or set ADB=/path/to/adb.")


class Adb:
    def __init__(self, target):
        self.binary = find_adb()
        self.target = target

    def shell(self, command, timeout=120):
        result = subprocess.run(
            [self.binary, "-s", self.target, "shell", command],
            capture_output=True, text=True, errors="replace", timeout=timeout,
        )
        return result.stdout.replace("\r", "")

    def connect(self):
        if ":" in self.target:
            subprocess.run([self.binary, "connect", self.target], capture_output=True, timeout=30)
        state = subprocess.run(
            [self.binary, "-s", self.target, "get-state"],
            capture_output=True, text=True, timeout=30,
        )
        if state.stdout.strip() != "device":
            sys.exit(
                f"{self.target} is not ready ({state.stderr.strip() or state.stdout.strip()}).\n"
                "If it says unauthorized: run `adb kill-server`, connect again, and accept the\n"
                "prompt on the radio with 'Always allow'."
            )


def parse_package_paths(text):
    """`pm list packages -f` lines look like package:/data/app/x-abc==/base.apk=x."""
    paths = {}
    for line in text.splitlines():
        if line.startswith("package:") and "=" in line:
            path, package = line[len("package:"):].rsplit("=", 1)
            paths[path] = package
    return paths


def parse_packages(text):
    return {line[len("package:"):].strip() for line in text.splitlines() if line.startswith("package:")}


def parse_uids(text):
    uids = {}
    for line in text.splitlines():
        match = re.match(r"package:(\S+) uid:(\d+)", line)
        if match:
            uids.setdefault(match.group(2), []).append(match.group(1))
    return uids


def parse_md5(text):
    hashes = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{32}", parts[0]):
            hashes[parts[1].strip()] = parts[0]
    return hashes


def parse_connections(text):
    """Return (ip, port, uid) from /proc/net/tcp and tcp6, keeping IPv4 and IPv4-mapped peers."""
    connections = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 8 or fields[0] == "sl":
            continue
        address, port = fields[2].split(":")
        if len(address) == 32:
            if not address.startswith("0000000000000000FFFF0000"):
                continue
            address = address[-8:]
        ip = socket.inet_ntoa(struct.pack("<I", int(address, 16)))
        if ip != "0.0.0.0" and not ip.startswith("127."):
            connections.append((ip, int(port, 16), fields[7]))
    return connections


def read_list(path):
    packages = []
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            packages.append(line)
    return packages


def heading(title):
    print(f"\n== {title}")


def check(adb, iocs, targets):
    """Print a read-only report and return the list of indicators found."""
    findings = []

    heading("Device (what it really is, not what the settings screen says)")
    for label, prop in (
        ("Android", "ro.build.version.release"),
        ("SDK", "ro.build.version.sdk"),
        ("Security patch", "ro.build.version.security_patch"),
        ("Chip", "ro.hardware"),
        ("Model", "ro.product.model"),
    ):
        print(f"{label}: {adb.shell(f'getprop {prop}').strip()}")
    fake = adb.shell("getprop persist.meminfo.totalfake").strip()
    meminfo = adb.shell("dumpsys meminfo")
    for line in meminfo.splitlines():
        if re.match(r"\s*(Total|Lost) RAM:", line):
            print(line.strip())
    if fake:
        print(f"persist.meminfo.totalfake={fake}: the reported RAM total is probably inflated")

    heading("Vendor components")
    enabled = parse_packages(adb.shell("pm list packages -e"))
    disabled = parse_packages(adb.shell("pm list packages -d"))
    for package in targets:
        state = "ENABLED" if package in enabled else "disabled" if package in disabled else "not present"
        print(f"{state:12} {package}")
    variety = "ENABLED" if "com.dofun.variety" in enabled else "removed or disabled"
    print(f"{variety:12} com.dofun.variety (vendor launcher, see the README)")

    heading("Packages named in the report")
    every_package = adb.shell("pm list packages -f -u")
    paths = parse_package_paths(every_package)
    installed = set(paths.values())
    for package in iocs["packages"]:
        if package in installed:
            findings.append(f"package {package}")
            print(f"FOUND {package}")
    print(f"checked {len(iocs['packages'])} names against {len(installed)} packages")

    heading("TWCore download folder")
    listing = adb.shell(f"ls {TWCORE_CACHE}/push/apk/ 2>/dev/null").strip()
    if listing:
        findings.append(f"files in {TWCORE_CACHE}/push/apk/")
        print(f"FOUND files in {TWCORE_CACHE}/push/apk/:\n{listing}")
    else:
        print("empty or missing")

    heading("APK hashes")
    hashes = {}
    ordered = list(paths)
    for start in range(0, len(ordered), MD5_CHUNK):
        chunk = " ".join(f"'{path}'" for path in ordered[start:start + MD5_CHUNK])
        hashes.update(parse_md5(adb.shell(f"md5sum {chunk} 2>/dev/null", timeout=300)))
    known = {value.lower() for value in iocs["md5"]}
    for path, value in hashes.items():
        if value in known:
            findings.append(f"hash {value} at {path}")
            print(f"FOUND {value} {path}")
    print(f"hashed {len(hashes)} of {len(paths)} APKs")
    if len(hashes) < len(paths):
        print("WARNING: some APKs could not be read, so this check is incomplete")

    heading("Connections right now")
    connections = parse_connections(adb.shell("cat /proc/net/tcp /proc/net/tcp6"))
    uids = parse_uids(adb.shell("pm list packages -U"))
    bad_ips = set(iocs["ips"])
    for ip, port, uid in connections:
        owner = ",".join(uids.get(uid, [f"uid {uid}"])[:2])
        if ip in bad_ips:
            findings.append(f"connection to {ip}:{port} from {owner}")
            print(f"FOUND {ip}:{port} from {owner}")
        elif port in (80, 1883) and not ip.startswith(("10.", "192.168.")):
            print(f"note  {ip}:{port} from {owner} (unencrypted port, worth a look)")
    print(f"looked at {len(connections)} connections")

    heading("Processes and logs")
    pattern = re.compile("|".join(re.escape(text) for text in iocs["strings"]), re.IGNORECASE)
    for source, command in (("process", "ps -A -o NAME"), ("log", "logcat -d")):
        hits = sorted({match.group(0).lower() for match in pattern.finditer(adb.shell(command))})
        for hit in hits:
            findings.append(f"{source} mentions {hit}")
            print(f"FOUND {source} mentions {hit}")
    print("done")

    heading("Result")
    if findings:
        print(f"{len(findings)} indicator(s) found. Do not trust this unit; see docs/FINDINGS.md.")
    else:
        print("No indicators found.")
        print("This does not prove the unit is clean: later stages run from memory, and anything")
        print("removed earlier leaves no trace here. Only the published indicators are checked.")
    return findings


def ask(question):
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def apply_list(adb, targets, assume_yes=False, dry_run=False):
    installed = parse_packages(adb.shell("pm list packages -e"))
    print("Do this parked. After each app, test the reverse camera, audio and steering controls.")
    for package in targets:
        if package not in installed:
            print(f"skip    {package} (not enabled)")
            continue
        if dry_run:
            print(f"would disable {package}")
            continue
        if not assume_yes and not ask(f"Disable {package}?"):
            print(f"skip    {package}")
            continue
        print(adb.shell(f"pm disable-user --user 0 {package}").strip())


def revert_list(adb, targets, dry_run=False):
    disabled = parse_packages(adb.shell("pm list packages -d"))
    for package in targets:
        if package not in disabled:
            print(f"skip    {package} (not disabled)")
        elif dry_run:
            print(f"would enable {package}")
        else:
            print(adb.shell(f"pm enable {package}").strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["check", "apply", "revert"])
    parser.add_argument("target", help="adb serial or ip:port, as shown by `adb devices`")
    parser.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    parser.add_argument("--yes", action="store_true", help="apply: do not ask before each app")
    args = parser.parse_args()

    adb = Adb(args.target)
    adb.connect()
    targets = read_list(DISABLE_LIST)
    if args.command == "check":
        findings = check(adb, json.loads(IOC_FILE.read_text()), targets)
        sys.exit(EXIT_INDICATORS if findings else 0)
    if args.command == "apply":
        apply_list(adb, targets, assume_yes=args.yes, dry_run=args.dry_run)
    else:
        revert_list(adb, targets, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
