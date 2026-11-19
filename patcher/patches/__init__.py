"""Compatibility patches, applied in list order.

Each patch has a name, a description and apply(ctx), which returns a short
summary of what it changed, or "" when nothing needed changing.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable

from patcher.apk import Context, a


@dataclass
class Patch:
    name: str
    description: str
    apply: Callable[[Context], str]


def target_sdk(ctx: Context) -> str:
    """Android 14 refuses to install apps targeting SDK < 23."""
    want = ctx.options.target_sdk
    old = ctx.target_sdk
    if old >= want:
        return ""
    ctx.yml_set("targetSdkVersion", str(want), section="sdkInfo")
    # Drop any uses-sdk left in the manifest so apktool.yml is the single source.
    for el in ctx.manifest.findall("uses-sdk"):
        ctx.manifest.remove(el)
    return f"targetSdkVersion {old} -> {want}"


def exported_flags(ctx: Context) -> str:
    """Android 12+ (targetSdk 31+) requires android:exported on components with intent filters."""
    if ctx.options.target_sdk < 31:
        return ""
    n = 0
    for comp in ctx.components():
        if comp.get(a("exported")) is None and comp.find("intent-filter") is not None:
            comp.set(a("exported"), "true")
            n += 1
    return f"added android:exported to {n} components" if n else ""


def cleartext_traffic(ctx: Context) -> str:
    """Android 9+ (targetSdk 28+) blocks plain-HTTP traffic, which old game servers often used."""
    app = ctx.application
    if ctx.options.target_sdk < 28 or app.get(a("usesCleartextTraffic")) == "true":
        return ""
    app.set(a("usesCleartextTraffic"), "true")
    return "allowed plain-HTTP traffic"


def legacy_storage(ctx: Context) -> str:
    """Keep old external-storage behaviour for apps that save outside their sandbox."""
    perms = {p.get(a("name")) for p in ctx.manifest.findall("uses-permission")}
    if "android.permission.WRITE_EXTERNAL_STORAGE" not in perms:
        return ""
    if ctx.application.get(a("requestLegacyExternalStorage")) == "true":
        return ""
    ctx.application.set(a("requestLegacyExternalStorage"), "true")
    return "requested legacy external storage"


def extract_native_libs(ctx: Context) -> str:
    """Rebuilt APKs store .so files compressed; tell Android to extract them."""
    app = ctx.application
    if not ctx.abis() or app.get(a("extractNativeLibs")) == "true":
        return ""
    app.set(a("extractNativeLibs"), "true")
    return "set extractNativeLibs=true"


def strip_dead_permissions(ctx: Context) -> str:
    """Remove permissions that no longer exist or are refused on modern Android."""
    dead = {
        "android.permission.GET_TASKS",
        "android.permission.READ_LOGS",
        "android.permission.WRITE_SETTINGS",
        "android.permission.SYSTEM_ALERT_WINDOW",
        "com.android.launcher.permission.INSTALL_SHORTCUT",
        "com.android.launcher.permission.UNINSTALL_SHORTCUT",
    }
    removed = []
    for el in list(ctx.manifest.findall("uses-permission")):
        if el.get(a("name")) in dead:
            ctx.manifest.remove(el)
            removed.append(el.get(a("name")).rsplit(".", 1)[-1])
    return f"removed {', '.join(removed)}" if removed else ""


def rename_package(ctx: Context) -> str:
    """Optional (--package): lets the patched app install next to the original."""
    new = ctx.options.package
    if not new or new == ctx.package:
        return ""
    ctx.yml_set("renameManifestPackage", new)
    # apktool only rewrites the package attribute; providers' authorities must be unique too.
    old = ctx.package
    for prov in ctx.application.iter("provider"):
        auth = prov.get(a("authorities"))
        if auth and old in auth:
            prov.set(a("authorities"), auth.replace(old, new))
    return f"package -> {new}"


def app_name(ctx: Context) -> str:
    """Optional (--app-name): change the launcher label."""
    name = ctx.options.app_name
    if not name:
        return ""
    ctx.application.set(a("label"), name)
    for act in ctx.application.iter("activity"):
        categories = {c.get(a("name")) for c in act.iter("category")}
        if "android.intent.category.LAUNCHER" in categories:
            act.set(a("label"), name)
    return f"label -> {name}"


def abi_check(ctx: Context) -> str:
    """Report the CPU architectures the native code supports (no changes made)."""
    abis = ctx.abis()
    if not abis:
        ctx.warnings.append(
            "No native libraries found. If you pulled a split install, the libs live in a "
            "split_config.<abi>.apk next to base.apk; patch a full (non-split) APK instead.")
        return "no native libs"
    if "arm64-v8a" not in abis and "x86_64" not in abis:
        ctx.warnings.append(
            f"Native code is 32-bit only ({', '.join(abis)}). It will NOT run on 64-bit-only "
            "phones (e.g. Pixel 7 and newer, many 2023+ flagships). No APK patch can fix that "
            "without the game's source code.")
    return "ABIs: " + ", ".join(abis)


ALL_PATCHES = [
    Patch("target-sdk", "raise targetSdkVersion so Android 14+ allows installing", target_sdk),
    Patch("exported-flags", "add android:exported (only when targeting SDK 31+)", exported_flags),
    Patch("cleartext-traffic", "allow plain HTTP (only when targeting SDK 28+)", cleartext_traffic),
    Patch("legacy-storage", "keep old external-storage access", legacy_storage),
    Patch("extract-native-libs", "extract native libs at install time", extract_native_libs),
    Patch("strip-dead-permissions", "drop permissions modern Android refuses", strip_dead_permissions),
    Patch("rename-package", "rename package (--package)", rename_package),
    Patch("app-name", "change launcher label (--app-name)", app_name),
    Patch("abi-check", "report 32/64-bit native support", abi_check),
]
