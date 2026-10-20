import os
import pty
import select
import tempfile
import termios
import threading
import unittest
from pathlib import Path

from niimstudio.serial_transport import SerialTransport, discover_serial


class SerialTests(unittest.TestCase):
    def test_real_pseudoterminal_round_trip_and_settings_restore(self):
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        before = termios.tcgetattr(slave)
        received = bytearray()
        ready = threading.Event()
        disconnected = []

        def on_data(data):
            received.extend(data)
            ready.set()

        transport = SerialTransport(on_data, disconnected.append)
        try:
            transport.open(path)
            self.assertEqual(termios.tcgetattr(slave)[4], termios.B115200)
            packet = bytes.fromhex("5555010101aaaa")
            transport.write(packet)
            self.assertTrue(select.select([master], [], [], 2)[0])
            self.assertEqual(os.read(master, 1024), packet)
            response = bytes.fromhex("555581010081aaaa")
            os.write(master, response)
            self.assertTrue(ready.wait(2))
            self.assertEqual(received, response)
            transport.close()
            self.assertEqual(termios.tcgetattr(slave), before)
            self.assertEqual(disconnected, [])
            with self.assertRaises(ConnectionError):
                transport.write(packet)
            transport.close()  # idempotent
        finally:
            transport.close()
            os.close(master)
            os.close(slave)

    def test_serial_removal_notifies_once(self):
        master, slave = pty.openpty()
        ready = threading.Event()
        transport = SerialTransport(lambda _data: None, lambda _reason: ready.set())
        try:
            transport.open(os.ttyname(slave))
            os.close(master)
            self.assertTrue(ready.wait(2))
        finally:
            transport.close()
            os.close(slave)

    def test_regular_files_are_rejected(self):
        with tempfile.NamedTemporaryFile() as file:
            transport = SerialTransport(lambda _d: None, lambda _e: None)
            with self.assertRaises(ValueError):
                transport.open(file.name)
            self.assertIsNone(transport.fd)

    def test_discovery_only_lists_usb_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("ttyACM0", "ttyUSB1", "ttyS0", "tty0"):
                (root / name).mkdir()
            (root / "ttyACM0/product").write_text("NIIMBOT B1 Pro")
            devices = discover_serial(root, Path("/test/dev"))
            self.assertEqual([d["id"] for d in devices], ["/test/dev/ttyACM0", "/test/dev/ttyUSB1"])
            self.assertEqual(devices[0]["name"], "NIIMBOT B1 Pro")
