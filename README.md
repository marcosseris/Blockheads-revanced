# Blockheads ReVanced

A patcher that gets an old copy of **The Blockheads** for Android installing
and running on current Android versions. It works like ReVanced: **you supply
your own APK**. It unpacks it, applies compatibility patches, then rebuilds,
aligns and signs it.

This repo holds no game files and must never hold any. `.gitignore` blocks
APKs, the unpacked `work/` folder and the `out/` folder.

## Why old APKs break

| Problem | Symptom | Patch |
|---|---|---|
| Android 14+ refuses apps targeting SDK < 23 | "App not installed" / `INSTALL_FAILED_DEPRECATED_SDK_VERSION` | `target-sdk` |
| Re-packed native libs are compressed | Crash on launch: `UnsatisfiedLinkError` | `extract-native-libs` |
| Scoped storage on Android 10+ | Saves/exports fail | `legacy-storage` |
| Removed or restricted permissions | Install warnings or failures | `strip-dead-permissions` |
| Targeting SDK 28+ blocks plain HTTP | Online features fail | `cleartext-traffic` (only with `--target-sdk 28+`) |
| Targeting SDK 31+ needs `android:exported` | Install fails | `exported-flags` (only with `--target-sdk 31+`) |

## Usage

Requirements: Java 17+, Python 3.9+, `curl`, and `adb` if you pull the APK from a phone.

```bash
scripts/fetch-tools.sh                      # downloads apktool + uber-apk-signer (checksums verified)

# Get your APK: from a phone that still has the game installed...
scripts/pull-apk.sh                         # finds the package name
scripts/pull-apk.sh <package-name>          # copies it into input/
# ...or copy an APK you already have into input/

python3 patcher/patch.py input/base.apk     # -> out/base-revanced.apk
adb install out/base-revanced.apk
```

Options:

```
--target-sdk N     targetSdkVersion to set (default 23; higher turns on more patches but may break old code)
--package NAME     rename the package so it installs next to the original
--app-name NAME    change the launcher label
--exclude PATCH    skip a patch (see --list-patches)
--keep-work        keep the unpacked files in work/ so you can look at them
```

The first run creates `work/revanced.keystore`. **Keep it**: future patched
builds need the same key to install as updates without wiping your worlds.

## Before you install: back up your worlds

The patched APK is signed with your key, not the original developer's, so
Android won't install it over the original. You'll need to uninstall first,
**which deletes your saves** unless you back them up, or use
`--package` to install it next to the original.

## Limits (things no APK patch can fix)

- **64-bit-only phones.** If the game only ships 32-bit (`armeabi-v7a`) native
  code, it can't run on 64-bit-only devices such as Pixel 7 and newer. The
  patcher's `abi-check` warns you if that applies.
- **Online services.** Multiplayer, cloud saves and server lists depend on the
  original servers. If those are offline, patching won't bring them back.
- **In-app purchases.** Google Play billing won't work with a re-signed APK.
  This project doesn't bypass licensing or purchases.
- **Split APKs.** If `pull-apk.sh` gets `base.apk` plus `split_config.*.apk`
  files, the native code is in the split files. You need a full APK.

## Testing

```bash
tests/selftest.sh
```

This builds a fake legacy APK (targets SDK 10, 32-bit libs only, outdated
permissions), patches it and checks every patch landed and the signature
(v1/v2/v3) verifies. No game files are needed.

## Adding a patch

Add a function to `patcher/patches/__init__.py` that takes the `Context`,
edits `ctx.manifest` (an ElementTree root) or `ctx.yml`, and returns a short
summary string (or `""` if nothing changed). Then register it in `ALL_PATCHES`.

## Legal

The Blockheads is © Majic Jungle Software. This project isn't affiliated with
it. Only patch a copy you legitimately own, and don't redistribute patched APKs.
