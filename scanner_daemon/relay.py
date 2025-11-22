import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO  # type: ignore
except ImportError:  # pragma: no cover - not available on non-Pi
    GPIO = None


class RelayController:
    def __init__(self, pin: int | None, active_low: bool = True):
        self.pin = pin
        self.active_low = active_low
        self.is_open = False
        self._lock = asyncio.Lock()
        self._available = False

        if pin is None:
            logger.warning("Relay not configured (RELAY_GPIO_PIN missing); door open will be skipped.")
            return
        if GPIO is None:
            logger.warning("RPi.GPIO not available; running in no-relay mode.")
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            self._set_closed_state()
            self._available = True
            logger.info("Relay initialized on GPIO pin %s (active_low=%s)", self.pin, self.active_low)
        except Exception as exc:  # pragma: no cover - hw-specific
            logger.error("Failed to initialize relay on pin %s: %s", self.pin, exc, exc_info=True)
            self._available = False

    def _set_open_state(self):
        if GPIO is None or self.pin is None:
            return
        GPIO.output(self.pin, GPIO.LOW if self.active_low else GPIO.HIGH)

    def _set_closed_state(self):
        if GPIO is None or self.pin is None:
            return
        GPIO.output(self.pin, GPIO.HIGH if self.active_low else GPIO.LOW)

    async def open(self, duration_seconds: int):
        if not self._available:
            logger.warning("Relay not available; skipping door open command.")
            return
        async with self._lock:
            if self.is_open:
                logger.warning("Door already open; ignoring duplicate command.")
                return
            self.is_open = True
            try:
                logger.info("Door open started for %ss", duration_seconds)
                self._set_open_state()
                await asyncio.sleep(max(0, duration_seconds))
            except Exception as exc:  # pragma: no cover - hw-specific
                logger.error("Error while operating relay: %s", exc, exc_info=True)
            finally:
                try:
                    self._set_closed_state()
                except Exception as exc:  # pragma: no cover - hw-specific
                    logger.error("Failed to close relay: %s", exc, exc_info=True)
                self.is_open = False
                logger.info("Door open finished")

    def cleanup(self):
        if GPIO is None or not self._available:
            return
        try:
            self._set_closed_state()
            GPIO.cleanup(self.pin)
        except Exception as exc:  # pragma: no cover - hw-specific
            logger.error("Error during relay cleanup: %s", exc, exc_info=True)
