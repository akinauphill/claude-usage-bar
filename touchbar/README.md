# usage-bar: Touch Bar version

**Your Claude Code usage on the Touch Bar of a MacBook Pro running Linux, shown while a terminal is focused and gone when you tab away.**

```
[esc] [☼] [☀] [⌨] [⌨]    5h ████░░░░ 37% ↻2h14m   7d █░░░░░░░ 12%   ctx ███░░░ 41%   cost $1.23
```

The band-above-the-prompt version in the [repo root](../README.md) needs nothing but Claude Code. This one is for a **2016 or 2017 Touch Bar MacBook Pro driven by [t1bridge](https://github.com/standardagents/t1bridge)** and is a separate plugin, `usage-bar-touchbar`. You can install both.

## How it fits together

Three small pieces, because Claude Code can't see your Touch Bar and GNOME on Wayland won't tell anyone which window has focus:

1. **The mod** (`hooks/register.ts`) writes your usage to `$XDG_RUNTIME_DIR/usage-bar/usage.json` after every turn.
2. **A GNOME Shell extension** (`gnome-extension/`) writes the focused window's class and title to `$XDG_RUNTIME_DIR/usage-bar/focus.json`. That's all it does.
3. **A Touch Bar renderer** (`renderer/usage-touchbar`, Python + cairo) that t1bridge runs instead of its built-in one. It draws the usage readout when the focused window is a terminal.

t1bridge allows one renderer at a time, so this one is a full bar, laid out like macOS's expanded Control Strip: **Esc, screen brightness, keyboard light, previous / play-pause / next, mute and volume** (tap to step; **press and hold for macOS's slider**: it opens at the right end of the bar, stays open after you lift, and closes with its × button, a touch elsewhere, or 4 s untouched), **F1-F12 while Fn is held**, and the **Touch ID overlay** with its cancel button.

While a terminal is focused, the usage readout takes the middle and the controls shrink into a strip on the right (screen, keyboard light, play-pause, mute, volume). Previous and next come back when you tab away. Taps on the readout do nothing.

Volume and mute go through PipeWire's `wpctl`; media keys go to whichever MPRIS player is playing (Spotify, browsers, mpv...) through `gdbus`. Without those tools the matching buttons are hidden.

## Who this is for

You'll get the most out of it if:

- you're on a **Touch Bar MacBook Pro** with t1bridge already working (the Touch Bar lights up and Esc works),
- you use **GNOME on Wayland** (tested on GNOME Shell 50) and a terminal like Ghostty, kitty or Alacritty.

It is **not** for you if:

- your Touch Bar isn't running t1bridge's renderer service yet. Start with [t1-revive](https://github.com/niconistal/t1-revive) and t1bridge,
- you're on KDE or X11. The renderer works, but you'd need your own focus source (or set `"focus": "always"`, below).

## Install

You need `python-cairo` (`sudo pacman -S python-cairo` on Arch). Then:

```bash
git clone https://github.com/akinauphill/claude-usage-bar
cd claude-usage-bar/touchbar
./install.sh
```

It symlinks the renderer to `~/.config/t1bridge/renderer`, copies the extension to `~/.local/share/gnome-shell/extensions/`, and restarts only your user service, `t1-touchbar.service`. It also makes that service start with your graphical session, since as shipped it stops at logout and doesn't come back. It touches nothing root-level.

GNOME only loads a *new* extension at login, so **log out and back in once, then run `gnome-extensions enable usage-bar-focus@usage-bar`**. Until then the usage readout stays hidden (the bar behaves like the stock one) because the renderer can't tell what's focused.

Then add the mod so Claude Code writes the numbers:

```
/plugin install usage-bar-touchbar --marketplace akinauphill/claude-usage-bar
```

## If anything goes wrong

```bash
./uninstall.sh
```

or by hand: `rm ~/.config/t1bridge/renderer && systemctl --user restart t1-touchbar.service`.

If the renderer crashes, t1bridge falls back to its built-in bar by itself. If the connection to the hardware service drops (screen lock, suspend), the renderer reconnects with backoff, the same way the built-in one does.

## If you use keyd

[keyd](https://github.com/rvaiya/keyd) grabs the keyboard, so with a config like `fn = layer(fn)` t1bridge never sees Fn and the bar never shows F1-F12. The renderer works around it by following keyd's layer through `keyd listen`. That needs your user in the `keyd` group:

```bash
sudo usermod -aG keyd "$USER"   # then log out and back in
```

Your keyd Fn shortcuts keep working; the bar just shows the F-row while the `fn` layer is on. Set `"keydLayer"` in the config if your layer has another name, or `""` to turn this off.

## Config

Optional, `~/.config/usage-bar/touchbar.json`:

```json
{
  "focus": "extension",
  "terminals": ["ghostty", "kitty"],
  "titleContains": "claude"
}
```

| Key | Default | What it is |
|---|---|---|
| `focus` | `"extension"` | `"always"` shows usage whether or not a terminal is focused (and works without the extension) |
| `terminals` | a list of common terminals | Substrings of the window class / app id that count as "a terminal" |
| `keydLayer` | `"fn"` | The keyd layer that counts as Fn held (see above). `""` turns it off |
| `titleContains` | `""` | Only count a terminal whose title contains this. Claude Code sets the title, so `"claude"` limits it to windows running it |

## Known limitations

- **Tested lightly.** The protocol is tested against a fake hardware service, the layout and drawing against rendered frames, and the mod passes `claude plugin validate`. How it *feels* on the real bar (touch accuracy, repeat timing) has had little testing, and the look is not pixel-identical to the built-in bar.
- **No t1bridge desktop provider support.** Volume and media are done directly with `wpctl` and MPRIS instead, so there's no on-screen volume popup.
- **No display-off handling.** t1bridge's built-in renderer blanks when the desktop blanks the display. This one doesn't yet.
- **Several Claude Code sessions share one readout.** The last one to report wins.
- **GNOME only for focus**, and the extension needs a login to load.

## How this was made

**AI disclosure:** this was written with an AI coding assistant (Claude), against t1bridge's published renderer interface. Treat it as **experimental**, and mind that a custom renderer sits between you and your Esc key. The fallback and `uninstall.sh` are there for that reason.

## License

MIT, see [LICENSE](../LICENSE).
