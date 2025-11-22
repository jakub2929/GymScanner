import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class ScannerConfig:
    backend_base_url: str
    api_key: str
    scanner_in_device: str
    scanner_out_device: str
    device_id_in: str = "in-1"
    device_id_out: str = "out-1"
    scanner_in_mode: str = "hid"
    scanner_out_mode: str = "hid"
    log_path: str = "/var/log/gym-scanner-daemon.log"
    log_level: str = "INFO"
    request_timeout: float = 5.0
    retry_attempts: int = 3
    retry_backoff: float = 0.5
    relay_gpio_pin: int | None = None
    relay_active_low: bool = True

    @classmethod
    def from_env(cls) -> "ScannerConfig":
        """
        Load configuration from environment variables or .env file.
        """
        load_dotenv()
        backend_base_url = os.getenv("BACKEND_BASE_URL")
        api_key = os.getenv("TURNSTILE_API_KEY")
        scanner_in_device = os.getenv("SCANNER_IN_DEVICE")
        scanner_out_device = os.getenv("SCANNER_OUT_DEVICE")

        if not backend_base_url or not api_key:
            raise ValueError("BACKEND_BASE_URL and TURNSTILE_API_KEY are required")
        if not scanner_in_device or not scanner_out_device:
            raise ValueError("SCANNER_IN_DEVICE and SCANNER_OUT_DEVICE are required")

        return cls(
            backend_base_url=backend_base_url.rstrip("/"),
            api_key=api_key,
            scanner_in_device=scanner_in_device,
            scanner_out_device=scanner_out_device,
            device_id_in=os.getenv("DEVICE_ID_IN", "in-1"),
            device_id_out=os.getenv("DEVICE_ID_OUT", "out-1"),
            scanner_in_mode=os.getenv("SCANNER_IN_MODE", "hid"),
            scanner_out_mode=os.getenv("SCANNER_OUT_MODE", "hid"),
            log_path=os.getenv("LOG_PATH", "/var/log/gym-scanner-daemon.log"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", 5.0)),
            retry_attempts=int(os.getenv("RETRY_ATTEMPTS", 3)),
            retry_backoff=float(os.getenv("RETRY_BACKOFF", 0.5)),
            relay_gpio_pin=int(os.getenv("RELAY_GPIO_PIN")) if os.getenv("RELAY_GPIO_PIN") else None,
            relay_active_low=os.getenv("RELAY_ACTIVE_LOW", "true").lower() == "true",
        )
