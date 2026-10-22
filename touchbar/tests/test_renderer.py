import importlib.machinery
import importlib.util
import json
import mmap
import os
import socket
import struct
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "renderer", "usage-touchbar")
loader = importlib.machinery.SourceFileLoader("usage_touchbar", PATH)
spec = importlib.util.spec_from_loader("usage_touchbar", loader)
r = importlib.util.module_from_spec(spec)
loader.exec_module(r)


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.layout = r.Layout(2170, 60)

    def test_escape_and_controls(self):
        self.assertEqual(self.layout.action_at(10, 30, False), "escape")
        self.assertEqual(self.layout.action_at(200, 30, False), "display_down")
        self.assertEqual(self.layout.action_at(800, 30, False), "keyboard_up")
        self.assertEqual(self.layout.action_at(1100, 30, False), "media_previous")
        self.assertEqual(self.layout.action_at(2100, 30, False), "volume_up")

    def test_focused_layout_has_usage_in_the_middle_and_a_strip_on_the_right(self):
        self.assertIsNone(self.layout.action_at(800, 30, False, compact=True))  # usage: not touchable
        self.assertEqual(self.layout.action_at(2160, 30, False, compact=True), "volume_up")
        strip = [name for name, _x, _w in self.layout.controls(compact=True)]
        self.assertEqual(strip[0], "display_down")
        left, width = self.layout.usage_area()
        self.assertLess(left + width, self.layout.controls(compact=True)[0][1])

    def test_no_wpctl_hides_volume(self):
        layout = r.Layout(2170, 60, audio=False)
        self.assertIsNone(layout.action_at(2100, 30, False))

    def test_fn_row_is_esc_plus_twelve_slots(self):
        self.assertEqual(self.layout.action_at(10, 30, True), "escape")
        self.assertEqual(self.layout.action_at(2160, 30, True), ("fn", 11))
        self.assertEqual(self.layout.action_at(170, 30, True), ("fn", 0))

    def test_overlay_swallows_everything_right_of_esc(self):
        self.assertEqual(self.layout.action_at(10, 30, False, overlay=True), "escape")
        self.assertIsNone(self.layout.action_at(400, 30, False, overlay=True))

    def test_unavailable_brightness_classes_are_hidden(self):
        layout = r.Layout(2170, 60, display=False)
        self.assertIsNone(layout.action_at(200, 30, False))
        self.assertEqual(layout.action_at(800, 30, False), "keyboard_up")


class FormatTests(unittest.TestCase):
    def test_blocks(self):
        usage = {"windows": [{"kind": "five_hour", "percentUsed": 37.0, "resetsAt": "2026-01-01T02:05:00Z"}],
                 "contextPercent": 41, "costUsd": 1.234}
        now = 1767225600.0  # 2026-01-01T00:00:00Z
        self.assertEqual(r.usage_blocks(usage, now),
                         [("5h", "37%", 37.0, "2h05m"), ("ctx", "41%", 41, ""), ("cost", "$1.23", None, "")])

    def test_focus(self):
        cfg = {"focus": "extension", "terminals": ["ghostty"], "titleContains": ""}
        self.assertTrue(r.is_focused(cfg, {"wmClass": "com.mitchellh.ghostty", "title": "x"}))
        self.assertFalse(r.is_focused(cfg, {"wmClass": "firefox"}))
        self.assertFalse(r.is_focused(cfg, None))  # no extension: stock bar
        self.assertTrue(r.is_focused({**cfg, "focus": "always"}, None))
        self.assertFalse(r.is_focused({**cfg, "titleContains": "claude"}, {"wmClass": "ghostty", "title": "vim"}))


class KeydTests(unittest.TestCase):
    def test_keyd_layer_shows_the_function_row(self):
        session = r.Session.__new__(r.Session)  # just the input state, no connection
        session.keyd = r.KeydFn("")
        session.hw_fn, session.fn_held, session.dirty, session.touch = False, False, False, None
        session.keyd.active = True
        session.keyd.changed.set()
        session.poll_keyd()
        self.assertTrue(session.fn_held)
        self.assertTrue(session.dirty)
        session.keyd.active = False
        session.keyd.changed.set()
        session.poll_keyd()
        self.assertFalse(session.fn_held)


class SliderTests(unittest.TestCase):
    def make_session(self):
        session = r.Session.__new__(r.Session)  # input state only; sends are recorded
        sent = []
        session.conn = type("Conn", (), {"send": lambda self, mtype, payload=b"", fds=(): sent.append((mtype, payload))})()
        session.layout = r.Layout(2170, 60)
        session.keyd = r.KeydFn("")
        session.audio = type("Audio", (), {"available": True, "volume": 40, "muted": False,
                                           "set_level": lambda self, v: sent.append(("volume", v))})()
        session.hw_fn = session.fn_held = session.dirty = False
        session.touch = session.slider = None
        session.view = {"usage": None, "overlay": None}
        return session, sent

    def test_hold_opens_slider_and_drag_sets_level(self):
        session, sent = self.make_session()
        session.on_input(False, [(1900, 30)])  # volume_down
        session.touch = (session.touch[0], session.touch[1], 0.0, False)  # pretend the hold elapsed
        session.tick_repeat()
        self.assertEqual(session.slider["kind"], "volume")
        self.assertEqual(session.slider["level"], 40)
        _left, track_w = r.slider_track(session.layout)
        session.on_input(False, [(1900 - track_w // 4, 30)])  # drag left a quarter of the track
        self.assertEqual(session.slider["level"], 15)
        session.on_input(False, [])  # lift: final level sent, slider stays open
        self.assertEqual(sent[-1], ("volume", 15))
        self.assertEqual(session.slider["mode"], "idle")
        self.assertFalse([m for m, _ in sent if m == r.TAP_KEYS])

    def open_volume_slider(self, session):
        session.on_input(False, [(1900, 30)])
        session.touch = (session.touch[0], session.touch[1], 0.0, False)
        session.tick_repeat()
        session.on_input(False, [])

    def test_slider_sits_on_the_right_and_leaves_the_rest_of_the_bar(self):
        left, width = r.slider_region(r.Layout(2170, 60))
        self.assertGreater(left, 1000)
        self.assertEqual(left + width, 2170)

    def test_touching_the_track_puts_the_knob_there(self):
        session, sent = self.make_session()
        self.open_volume_slider(session)
        track_left, track_w = r.slider_track(session.layout)
        session.on_input(False, [(track_left + track_w * 3 // 4, 30)])
        session.on_input(False, [])
        self.assertEqual(sent[-1], ("volume", 75))
        self.assertIsNotNone(session.slider)

    def test_close_button_and_idle_close(self):
        session, sent = self.make_session()
        self.open_volume_slider(session)
        close_left, close_w = r.slider_close(session.layout)
        session.on_input(False, [(close_left + close_w // 2, 30)])
        self.assertIsNotNone(session.slider)  # closes on lift, like a button
        session.on_input(False, [])
        self.assertIsNone(session.slider)
        self.open_volume_slider(session)
        session.slider["last_touch"] -= r.SLIDER_IDLE_CLOSE + 1
        session.tick_repeat()
        self.assertIsNone(session.slider)

    def test_touch_elsewhere_closes_slider_and_works(self):
        session, sent = self.make_session()
        self.open_volume_slider(session)
        session.on_input(False, [(20, 30)])  # esc
        self.assertIsNone(session.slider)
        session.on_input(False, [])
        self.assertIn((r.TAP_KEYS, bytes([1, 0, 0, 0]) + bytes([1, 0, 0, 0, 0, 0, 0, 0])), sent)

    def test_tap_still_steps(self):
        session, sent = self.make_session()
        session.on_input(False, [(400, 30)])  # display_up
        session.on_input(False, [])
        self.assertEqual(sent, [(r.STEP_DISPLAY, bytes([1]))])
        self.assertIsNone(session.slider)

    def test_display_slider_sends_absolute_brightness(self):
        session, sent = self.make_session()
        session.on_input(False, [(400, 30)])
        session.touch = (session.touch[0], session.touch[1], 0.0, False)
        r.sysfs_percent = lambda pattern: 50
        session.tick_repeat()
        _left, track_w = r.slider_track(session.layout)
        session.on_input(False, [(400 + track_w // 5, 30)])
        session.on_input(False, [])
        self.assertEqual(sent[-1], (r.SET_DISPLAY, bytes([70])))


class FakeService(threading.Thread):
    """A hardware service that answers the T1HW handshake, takes a frame and sends input."""

    def __init__(self, path):
        super().__init__(daemon=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.server.bind(path)
        self.server.listen(4)
        self.hellos, self.keys, self.steps, self.frame = [], [], [], None
        self.got_frame = threading.Event()
        self.stop = False

    def run(self):
        while not self.stop:
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            self.serve(conn)

    def reply(self, conn, mtype, rid, payload=b""):
        conn.send(r.pack(mtype, payload, rid))

    def serve(self, conn):
        mem = None
        in_flight = None
        try:
            while True:
                msg, fds, _f, _a = socket.recv_fds(conn, 65536, 1)
                if not msg:
                    return
                mtype, rid, payload = r.unpack(msg)
                if mtype == r.HELLO:
                    minor, _res, features = struct.unpack("<HHQ", payload)
                    self.hellos.append(features)
                    if features & r.FEATURE_KEYBOARD:  # pretend: no keyboard backlight on this machine
                        self.reply(conn, r.ERROR, rid, struct.pack("<I", 2))
                        return
                    self.reply(conn, r.HELLO_ACK, rid, struct.pack("<HHIIII", 1, 0, 2170, 60, 1, 3))
                elif mtype == r.REGISTER_BUFFER:
                    bid, stride, length = struct.unpack("<IIQ", payload)
                    mem = mmap.mmap(fds[0], length, prot=mmap.PROT_READ)
                    self.reply(conn, r.ACK, rid)
                    # the first input frame: Fn up, finger down on esc, then lifted
                    for contacts in ([(20, 30)], []):
                        body = struct.pack("<QBBH", time.monotonic_ns(), 0, len(contacts), 0)
                        for x, y in contacts:
                            body += struct.pack("<BBBBII", 0, 1, 1, 0, x, y)
                        conn.send(r.pack(r.INPUT_FRAME, body))
                elif mtype == r.SUBMIT_FRAME:
                    bid, frame_id, damage = struct.unpack("<IQI", payload)
                    self.frame = bytes(mem[:])
                    self.reply(conn, r.ACK, rid)
                    conn.send(r.pack(r.FRAME_RELEASED, struct.pack("<IQ", bid, frame_id)))
                    self.got_frame.set()
                elif mtype == r.TAP_KEYS:
                    count, *_rest = struct.unpack_from("<BBBB", payload)
                    self.keys.append(struct.unpack_from("<4H", payload, 4)[:count])
                elif mtype in (r.STEP_DISPLAY, r.STEP_KEYBOARD):
                    self.steps.append((mtype, payload[0]))
        except OSError:
            return


class ProtocolTest(unittest.TestCase):
    def test_handshake_frame_and_esc_tap(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_RUNTIME_DIR"] = tmp
            os.environ["XDG_CONFIG_HOME"] = tmp
            os.makedirs(os.path.join(tmp, "usage-bar"))
            with open(os.path.join(tmp, "usage-bar", "usage.json"), "w") as f:
                json.dump({"windows": [], "contextPercent": 41, "costUsd": 2.0, "updatedAt": time.time() * 1000}, f)
            os.makedirs(os.path.join(tmp, "usage-bar"), exist_ok=True)
            with open(os.path.join(tmp, "usage-bar", "touchbar.json"), "w") as f:
                json.dump({"focus": "always"}, f)
            sock_path = os.path.join(tmp, "touchbar.sock")
            service = FakeService(sock_path)
            service.start()
            session = r.Session(sock_path, r.load_config())
            self.assertEqual((session.width, session.height), (2170, 60))
            self.assertTrue(session.features & r.FEATURE_DISPLAY)
            self.assertFalse(session.features & r.FEATURE_KEYBOARD)  # the probe was refused
            deadline = time.time() + 5
            session.view["now_epoch"] = time.time()
            while not service.got_frame.is_set() and time.time() < deadline:
                session.poll_inputs()
                if session.dirty and not session.in_flight:
                    session.render_and_submit()
                import select
                if select.select([session.conn.sock], [], [], 0.05)[0]:
                    mtype, _rid, payload = session.conn.recv()
                    if mtype == r.INPUT_FRAME:
                        session.on_input(*r.parse_input_frame(payload))
                    elif mtype == r.FRAME_RELEASED:
                        session.in_flight = False
            self.assertTrue(service.got_frame.is_set())
            self.assertEqual(len(service.frame), 2170 * 60 * 4)
            # the context readout is in the frame: some green pixels right of the controls
            row = 38
            right = service.frame[(row * 2170 + 1200) * 4:(row * 2170 + 2100) * 4]
            self.assertTrue(any(right[i + 1] > 150 for i in range(0, len(right), 4)))
            # drain the remaining input (finger lifted over esc): an Esc tap was sent
            deadline = time.time() + 2
            while not service.keys and time.time() < deadline:
                import select
                if select.select([session.conn.sock], [], [], 0.05)[0]:
                    mtype, _rid, payload = session.conn.recv()
                    if mtype == r.INPUT_FRAME:
                        session.on_input(*r.parse_input_frame(payload))
            self.assertEqual(service.keys, [(r.KEY_ESC,)])
            service.stop = True


if __name__ == "__main__":
    unittest.main()
