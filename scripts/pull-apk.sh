#!/usr/bin/env bash
# Copies an installed app's APK(s) off a USB-connected Android device into input/.
# Usage: scripts/pull-apk.sh [package-name]
# With no argument, lists installed packages whose name contains "blockheads".
set -euo pipefail
cd "$(dirname "$0")/.."
command -v adb >/dev/null || { echo "adb not found (install Android platform-tools)"; exit 1; }

if [[ $# -eq 0 ]]; then
  echo "Installed packages matching 'blockheads':"
  adb shell pm list packages | sed 's/^package://' | grep -i blockheads || echo "  (none found)"
  echo "Re-run with the package name: $0 <package>"
  exit 0
fi

pkg=$1
mkdir -p input
mapfile -t paths < <(adb shell pm path "$pkg" | tr -d '\r' | sed 's/^package://')
[[ ${#paths[@]} -gt 0 ]] || { echo "Package $pkg is not installed"; exit 1; }
for p in "${paths[@]}"; do
  adb pull "$p" "input/$(basename "$p")"
done
if [[ ${#paths[@]} -gt 1 ]]; then
  echo "Note: this app is installed as split APKs. Patch base.apk; the patcher reports if it lacks native libs."
fi
echo "Saved to input/"
