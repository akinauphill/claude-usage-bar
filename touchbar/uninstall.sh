#!/usr/bin/env bash
# Puts t1bridge's built-in Touch Bar renderer back and removes the focus extension.
set -euo pipefail

uuid="usage-bar-focus@usage-bar"
conf_dir="${XDG_CONFIG_HOME:-$HOME/.config}/t1bridge"

[ -L "$conf_dir/renderer" ] && rm "$conf_dir/renderer"
gnome-extensions disable "$uuid" 2>/dev/null || true
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$uuid"
systemctl --user restart t1-touchbar.service
echo "built-in Touch Bar renderer restored"
