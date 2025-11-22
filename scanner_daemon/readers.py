import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import evdev
from evdev import ecodes
import serial


logger = logging.getLogger(__name__)


@dataclass
class ScannedCode:
    direction: str
    device_id: str
    raw: str
    scanned_at: datetime


class HIDScannerReader:
    def __init__(self, device_path: str, direction: str, device_id: str, queue: asyncio.Queue):
        self.device_path = device_path
        self.direction = direction
        self.device_id = device_id
        self.queue = queue
        self._stopped = False

    def stop(self):
        self._stopped = True

    @staticmethod
    def _key_to_char(event) -> str | None:
        key_map = {
            ecodes.KEY_0: "0", ecodes.KEY_1: "1", ecodes.KEY_2: "2", ecodes.KEY_3: "3",
            ecodes.KEY_4: "4", ecodes.KEY_5: "5", ecodes.KEY_6: "6", ecodes.KEY_7: "7",
            ecodes.KEY_8: "8", ecodes.KEY_9: "9",
            ecodes.KEY_A: "a", ecodes.KEY_B: "b", ecodes.KEY_C: "c", ecodes.KEY_D: "d",
            ecodes.KEY_E: "e", ecodes.KEY_F: "f", ecodes.KEY_G: "g", ecodes.KEY_H: "h",
            ecodes.KEY_I: "i", ecodes.KEY_J: "j", ecodes.KEY_K: "k", ecodes.KEY_L: "l",
            ecodes.KEY_M: "m", ecodes.KEY_N: "n", ecodes.KEY_O: "o", ecodes.KEY_P: "p",
            ecodes.KEY_Q: "q", ecodes.KEY_R: "r", ecodes.KEY_S: "s", ecodes.KEY_T: "t",
            ecodes.KEY_U: "u", ecodes.KEY_V: "v", ecodes.KEY_W: "w", ecodes.KEY_X: "x",
            ecodes.KEY_Y: "y", ecodes.KEY_Z: "z",
            ecodes.KEY_MINUS: "-", ecodes.KEY_EQUAL: "=",
            ecodes.KEY_SLASH: "/", ecodes.KEY_BACKSLASH: "\\",
        }
        if event.value != 1:  # only key down
            return None
        if event.code == ecodes.KEY_ENTER:
            return "\n"
        return key_map.get(event.code)

    async def run(self):
        """Read from HID device and push complete scans to queue."""
        while not self._stopped:
            try:
                device = evdev.InputDevice(self.device_path)
                logger.info("Listening to HID scanner %s (%s)", self.device_id, self.device_path)
                buffer = ""
                async for event in device.async_read_loop():
                    if self._stopped:
                        break
                    if event.type != ecodes.EV_KEY:
                        continue
                    char = self._key_to_char(event)
                    if char is None:
                        continue
                    if char == "\n":
                        raw = buffer.strip()
                        buffer = ""
                        if raw:
                            await self.queue.put(
                                ScannedCode(
                                    self.direction,
                                    self.device_id,
                                    raw,
                                    datetime.now(timezone.utc),
                                )
                            )
                        continue
                    buffer += char
            except FileNotFoundError:
                logger.error("HID device %s not found, retrying in 2s", self.device_path)
                await asyncio.sleep(2)
            except Exception as exc:
                logger.error("Error reading HID scanner %s: %s", self.device_id, exc, exc_info=True)
                await asyncio.sleep(1)


class SerialScannerReader:
    def __init__(self, device_path: str, direction: str, device_id: str, queue: asyncio.Queue):
        self.device_path = device_path
        self.direction = direction
        self.device_id = device_id
        self.queue = queue
        self._stopped = False

    def stop(self):
        self._stopped = True

    async def run(self):
        """Read from serial device and push complete scans to queue."""
        while not self._stopped:
            try:
                with serial.Serial(self.device_path, baudrate=9600, timeout=1) as ser:
                    logger.info("Listening to serial scanner %s (%s)", self.device_id, self.device_path)
                    while not self._stopped:
                        raw = ser.readline().decode(errors="ignore").strip()
                        if raw:
                            await self.queue.put(
                                ScannedCode(
                                    self.direction,
                                    self.device_id,
                                    raw,
                                    datetime.now(timezone.utc),
                                )
                            )
            except serial.SerialException as exc:
                logger.error("Serial device error on %s: %s", self.device_path, exc)
                await asyncio.sleep(2)
            except FileNotFoundError:
                logger.error("Serial device %s not found, retrying in 2s", self.device_path)
                await asyncio.sleep(2)
            except Exception as exc:
                logger.error("Error reading serial scanner %s: %s", self.device_id, exc, exc_info=True)
                await asyncio.sleep(1)
