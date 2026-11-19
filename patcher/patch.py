#!/usr/bin/env python3
"""Blockheads ReVanced patcher.

Unpacks an APK you supply, applies compatibility patches so it installs and
runs on current Android versions, then rebuilds, aligns and signs it.

    python3 patcher/patch.py input/base.apk
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from patcher import apk  # noqa: E402
from patcher.patches import ALL_PATCHES  # noqa: E402

TOOLS = ROOT / "tools"


def run(cmd: list[str]) -> None:
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def ensure_tools() -> None:
    missing = [j for j in ("apktool.jar", "uber-apk-signer.jar") if not (TOOLS / j).exists()]
    if missing:
        sys.exit(f"Missing {', '.join(missing)}. Run scripts/fetch-tools.sh first.")
    if not shutil.which("java"):
        sys.exit("Java is required (JDK 17 or newer).")
    if not shutil.which("keytool"):
        sys.exit("keytool is required (it ships with the JDK).")


def ensure_keystore(path: Path, password: str) -> None:
    if path.exists():
        return
    print(f"Creating signing key {path} (keep it: updates must use the same key)")
    path.parent.mkdir(parents=True, exist_ok=True)
    run([
        "keytool", "-genkeypair", "-keystore", str(path), "-alias", "revanced",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
        "-storepass", password, "-keypass", password,
        "-dname", "CN=Blockheads ReVanced",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("apk", type=Path, nargs="?", help="APK to patch (your own copy)")
    ap.add_argument("-o", "--out", type=Path, help="output APK path (default: out/<name>-revanced.apk)")
    ap.add_argument("--target-sdk", type=int, default=23,
                    help="targetSdkVersion to set (default 23: the lowest Android 14+ will install)")
    ap.add_argument("--package", help="rename the package so it installs next to the original")
    ap.add_argument("--app-name", help="change the launcher label")
    ap.add_argument("--exclude", action="append", default=[], metavar="PATCH",
                    help="skip a patch by name (repeatable)")
    ap.add_argument("--list-patches", action="store_true", help="list patches and exit")
    ap.add_argument("--keystore", type=Path, default=ROOT / "work" / "revanced.keystore")
    ap.add_argument("--keystore-pass", default="revanced")
    ap.add_argument("--keep-work", action="store_true", help="keep the unpacked directory")
    args = ap.parse_args()

    if args.list_patches:
        for p in ALL_PATCHES:
            print(f"{p.name:22} {p.description}")
        return 0

    if args.apk is None:
        ap.error("an APK path is required")
    if not args.apk.is_file():
        sys.exit(f"{args.apk} not found")
    ensure_tools()

    work = ROOT / "work" / args.apk.stem
    out = args.out or ROOT / "out" / f"{args.apk.stem}-revanced.apk"
    unsigned = work.with_suffix(".unsigned.apk")

    print(f"[1/4] Unpacking {args.apk}")
    if work.exists():
        shutil.rmtree(work)
    # --no-src keeps classes.dex untouched; we only need to edit the manifest and resources.
    run(["java", "-jar", str(TOOLS / "apktool.jar"), "d", "--no-src", "-f", "-o", str(work), str(args.apk)])

    print("[2/4] Applying patches")
    ctx = apk.Context(work, args)
    print(f"  package {ctx.package}, version {ctx.version_name}, SDK {ctx.min_sdk}->{ctx.target_sdk}")
    for patch in ALL_PATCHES:
        if patch.name in args.exclude:
            print(f"  - {patch.name}: skipped")
            continue
        result = patch.apply(ctx)
        print(f"  {'+' if result else '-'} {patch.name}: {result or 'nothing to do'}")
    ctx.save()

    print("[3/4] Rebuilding")
    run(["java", "-jar", str(TOOLS / "apktool.jar"), "b", "-f", "-o", str(unsigned), str(work)])

    print("[4/4] Aligning and signing")
    ensure_keystore(args.keystore, args.keystore_pass)
    signed_dir = work.parent / "signed"
    if signed_dir.exists():
        shutil.rmtree(signed_dir)
    run([
        "java", "-jar", str(TOOLS / "uber-apk-signer.jar"), "--apks", str(unsigned),
        "--out", str(signed_dir), "--ks", str(args.keystore), "--ksAlias", "revanced",
        "--ksPass", args.keystore_pass, "--ksKeyPass", args.keystore_pass,
    ])
    produced = next(signed_dir.glob("*.apk"))
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(produced, out)
    shutil.rmtree(signed_dir)
    unsigned.unlink(missing_ok=True)
    if not args.keep_work:
        shutil.rmtree(work)

    print(f"\nDone: {out}")
    for w in ctx.warnings:
        print(f"WARNING: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
