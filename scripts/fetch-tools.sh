#!/usr/bin/env bash
# Downloads the pinned build tools into tools/ and verifies their checksums.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tools

fetch() {
  local name=$1 url=$2 sha=$3
  if [[ -f tools/$name ]] && echo "$sha  tools/$name" | sha256sum -c --quiet 2>/dev/null; then
    echo "ok   $name"; return
  fi
  echo "get  $name"
  curl -fsSL -o "tools/$name.part" "$url"
  echo "$sha  tools/$name.part" | sha256sum -c --quiet
  mv "tools/$name.part" "tools/$name"
}

fetch apktool.jar \
  https://github.com/iBotPeaches/Apktool/releases/download/v2.10.0/apktool_2.10.0.jar \
  c0350abbab5314248dfe2ee0c907def4edd14f6faef1f5d372d3d4abd28f0431
fetch uber-apk-signer.jar \
  https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar \
  e1299fd6fcf4da527dd53735b56127e8ea922a321128123b9c32d619bba1d835
