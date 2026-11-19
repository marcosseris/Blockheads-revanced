"""Access to an apktool-decoded APK: the manifest, apktool.yml and native libs."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID_NS)
ET.register_namespace("tools", "http://schemas.android.com/tools")


def a(attr: str) -> str:
    """Qualified name for an android: attribute."""
    return f"{{{ANDROID_NS}}}{attr}"


class Context:
    def __init__(self, work: Path, options) -> None:
        self.work = work
        self.options = options
        self.warnings: list[str] = []
        self.manifest_path = work / "AndroidManifest.xml"
        self.yml_path = work / "apktool.yml"
        self.tree = ET.parse(self.manifest_path)
        self.manifest = self.tree.getroot()
        self.yml = self.yml_path.read_text()

    # --- manifest -------------------------------------------------------
    @property
    def package(self) -> str:
        return self.manifest.get("package", "?")

    @property
    def application(self) -> ET.Element:
        app = self.manifest.find("application")
        if app is None:
            app = ET.SubElement(self.manifest, "application")
        return app

    def components(self):
        for tag in ("activity", "activity-alias", "service", "receiver", "provider"):
            yield from self.application.iter(tag)

    # --- apktool.yml (edited as text to avoid a YAML dependency) ---------
    def yml_get(self, key: str) -> str | None:
        m = re.search(rf"^\s*{key}:\s*'?([^'\n]*)'?\s*$", self.yml, re.M)
        return m.group(1).strip() if m else None

    def yml_set(self, key: str, value: str, section: str | None = None) -> None:
        pattern = rf"^(\s*{key}:\s*).*$"
        if re.search(pattern, self.yml, re.M):
            self.yml = re.sub(pattern, lambda m: f"{m.group(1)}'{value}'", self.yml, count=1, flags=re.M)
        elif section and re.search(rf"^{section}:\s*$", self.yml, re.M):
            self.yml = re.sub(rf"^({section}:\s*)$", rf"\1\n  {key}: '{value}'", self.yml, count=1, flags=re.M)
        else:
            self.yml += f"\n{section or ''}{':' if section else ''}\n  {key}: '{value}'\n"

    @property
    def min_sdk(self) -> int:
        return int(self.yml_get("minSdkVersion") or 1)

    @property
    def target_sdk(self) -> int:
        return int(self.yml_get("targetSdkVersion") or self.min_sdk)

    @property
    def version_name(self) -> str:
        return self.yml_get("versionName") or "?"

    # --- native code ----------------------------------------------------
    def abis(self) -> list[str]:
        lib = self.work / "lib"
        return sorted(p.name for p in lib.iterdir() if p.is_dir()) if lib.is_dir() else []

    def save(self) -> None:
        ET.indent(self.tree)
        self.tree.write(self.manifest_path, encoding="utf-8", xml_declaration=True)
        self.yml_path.write_text(self.yml)
