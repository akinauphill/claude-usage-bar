import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class FocusPublisher extends Extension {
    enable() {
        const dir = GLib.build_filenamev([GLib.get_user_runtime_dir(), 'usage-bar']);
        GLib.mkdir_with_parents(dir, 0o700);
        this._file = Gio.File.new_for_path(GLib.build_filenamev([dir, 'focus.json']));
        this._window = null;
        this._titleId = 0;
        this._focusId = global.display.connect('notify::focus-window', () => this._onFocus());
        this._onFocus();
    }

    disable() {
        global.display.disconnect(this._focusId);
        this._unwatch();
        try { this._file.delete(null); } catch (_e) { /* already gone */ }
        this._file = null;
    }

    _unwatch() {
        if (this._window && this._titleId)
            this._window.disconnect(this._titleId);
        this._window = null;
        this._titleId = 0;
    }

    _onFocus() {
        this._unwatch();
        this._window = global.display.focus_window;
        if (this._window)
            this._titleId = this._window.connect('notify::title', () => this._publish());
        this._publish();
    }

    _publish() {
        const w = this._window;
        const data = JSON.stringify({
            wmClass: w?.get_wm_class() ?? '',
            appId: w?.get_gtk_application_id() ?? '',
            title: w?.get_title() ?? '',
            ts: Date.now(),
        });
        try {
            this._file.replace_contents(new TextEncoder().encode(data), null, false,
                Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        } catch (e) {
            console.error(`usage-bar-focus: ${e.message}`);
        }
    }
}
