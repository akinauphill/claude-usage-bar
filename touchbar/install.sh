#!/usr/bin/env bash
# Installs the usage-bar Touch Bar renderer for t1bridge and the GNOME focus extension.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
renderer="$here/renderer/usage-touchbar"
uuid="usage-bar-focus@usage-bar"
ext_dir="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$uuid"
conf_dir="${XDG_CONFIG_HOME:-$HOME/.config}/t1bridge"

command -v t1bridge >/dev/null || { echo "t1bridge is not installed (see https://github.com/standardagents/t1bridge)" >&2; exit 1; }
python3 -c 'import cairo' 2>/dev/null || { echo "python-cairo is missing (Arch: sudo pacman -S python-cairo)" >&2; exit 1; }
[ -x "$renderer" ] || chmod +x "$renderer"

if [ -e "$conf_dir/renderer" ] && [ ! -L "$conf_dir/renderer" ]; then
  echo "$conf_dir/renderer exists and is not a symlink; not touching it" >&2; exit 1
fi
if [ -L "$conf_dir/renderer" ] && [ "$(readlink "$conf_dir/renderer")" != "$renderer" ]; then
  echo "note: replacing renderer selection $(readlink "$conf_dir/renderer")"
fi

mkdir -p "$conf_dir" "$ext_dir"
ln -sfn "$renderer" "$conf_dir/renderer"
cp "$here/gnome-extension/$uuid/"{metadata.json,extension.js} "$ext_dir/"

if gnome-extensions enable "$uuid" 2>/dev/null; then
  echo "focus extension enabled"
else
  echo "focus extension copied; after you log out and back in, run: gnome-extensions enable $uuid"
fi

# t1bridge's renderer unit is PartOf=graphical-session.target but only WantedBy=default.target,
# so it stops at logout and doesn't come back at the next login. Start it with the session.
systemctl --user add-wants graphical-session.target t1-touchbar.service >/dev/null 2>&1 || true

systemctl --user restart t1-touchbar.service
echo "renderer selected: $conf_dir/renderer -> $renderer"
echo "recover the stock bar any time: $here/uninstall.sh"
