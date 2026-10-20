"""USB serial at NiimBlue's 115200 baud, using Linux's standard termios API."""

import errno
import fcntl
import os
import select
import stat
import termios
import threading
import time
import tty
from pathlib import Path


def discover_serial(sys_root=Path("/sys/class/tty"), dev_root=Path("/dev")):
    devices = []
    for entry in sorted(sys_root.glob("tty*")):
        if not entry.name.startswith(("ttyUSB", "ttyACM")):
            continue
        product = "USB serial"
        for parent in (entry.resolve(), *entry.resolve().parents):
            try:
                product = (parent / "product").read_text().strip()
                break
            except OSError:
                continue
        node = dev_root / entry.name
        stable = next(
            (
                candidate
                for candidate in sorted((dev_root / "serial/by-id").glob("*"))
                if candidate.resolve() == node.resolve()
            ),
            node,
        )
        devices.append({"id": str(stable), "name": product, "kind": "serial"})
    return devices


class SerialTransport:
    def __init__(self, on_data, on_disconnect):
        self.on_data = on_data
        self.on_disconnect = on_disconnect
        self.fd = None
        self._stop = threading.Event()
        self._thread = None
        self._attributes = None

    def open(self, path):
        self._attributes = None
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            if not stat.S_ISCHR(os.fstat(fd).st_mode):
                raise ValueError("The selected device is not a serial port")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._attributes = termios.tcgetattr(fd)
            tty.setraw(fd)
            attrs = termios.tcgetattr(fd)
            attrs[4] = attrs[5] = termios.B115200
            attrs[2] |= termios.CLOCAL | termios.CREAD
            attrs[2] &= ~termios.CRTSCTS
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            termios.tcflush(fd, termios.TCIOFLUSH)
        except Exception:
            if self._attributes is not None:
                try:
                    termios.tcsetattr(fd, termios.TCSANOW, self._attributes)
                except (OSError, termios.error):
                    pass
            os.close(fd)
            raise
        self.fd = fd
        self._stop.clear()
        self._thread = threading.Thread(target=self._read, args=(fd,), daemon=True, name="niimstudio-serial")
        self._thread.start()

    def _read(self, fd):
        try:
            while not self._stop.is_set():
                if not select.select([fd], [], [], 0.2)[0]:
                    continue
                try:
                    chunk = os.read(fd, 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    raise ConnectionError("USB printer disconnected")
                self.on_data(chunk)
        except (OSError, ValueError, ConnectionError) as error:
            if not self._stop.is_set():
                self.on_disconnect(str(error))

    def write(self, data):
        if self.fd is None or self._stop.is_set():
            raise ConnectionError("USB printer is disconnected")
        data = memoryview(data)
        deadline = time.monotonic() + 10
        while data:
            if time.monotonic() >= deadline:
                raise TimeoutError("USB printer did not accept data within 10 seconds")
            try:
                written = os.write(self.fd, data)
                data = data[written:]
            except OSError as error:
                if error.errno != errno.EAGAIN:
                    raise
                select.select([], [self.fd], [], 0.1)

    def close(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        if self.fd is not None:
            try:
                if self._attributes is not None:
                    termios.tcsetattr(self.fd, termios.TCSANOW, self._attributes)
            except (OSError, termios.error):
                pass  # A physically removed port cannot have its attributes restored.
            os.close(self.fd)
            self.fd = None
