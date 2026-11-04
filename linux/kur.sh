#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ $(uname -m) != x86_64 ]] || ! grep -q '^VERSION_ID="24.04"$' /etc/os-release || ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo 'Bu kurulum Ubuntu 24.04 Desktop amd64 icindir.' >&2
  exit 1
fi
if [[ $EUID == 0 ]]; then
  echo 'Kurulumu normal kullanici olarak calistirin; sudo kullanmayin.' >&2
  exit 1
fi
PIXI=$(command -v pixi || true)
if [[ -z $PIXI && -x "$HOME/.pixi/bin/pixi" ]]; then PIXI="$HOME/.pixi/bin/pixi"; fi
if [[ -z $PIXI ]]; then
  echo 'Once https://pixi.sh/latest/installation/ adresindeki Linux kurulumunu tamamlayin.' >&2
  exit 1
fi
export UAV_COURSE_PIXI="$PIXI"
"$PIXI" install --manifest-path "$PWD/pixi.toml"
exec "$PIXI" run --manifest-path "$PWD/pixi.toml" python "$PWD/course.py" kur
