import asyncio
import logging
import signal
from dataclasses import dataclass

from scanner_daemon.config import ScannerConfig
from scanner_daemon.http_client import ScannerHttpClient
from scanner_daemon.logging_setup import setup_logging
from scanner_daemon.readers import HIDScannerReader, ScannedCode, SerialScannerReader
from scanner_daemon.relay import RelayController

logger = logging.getLogger(__name__)


@dataclass
class ScannerState:
    config: ScannerConfig
    http_client: ScannerHttpClient
    queue: asyncio.Queue
    relay: RelayController | None = None


def mask_token(token: str) -> str:
    if not token:
        return ""
    return f"{token[:4]}..." if len(token) > 4 else token


async def process_queue(state: ScannerState):
    while True:
        scan: ScannedCode = await state.queue.get()
        token = scan.raw.strip()
        if len(token) < 10:
            logger.debug(
                "Ignoring short token from %s (%s)",
                scan.device_id,
                mask_token(token),
            )
            state.queue.task_done()
            continue
        try:
            response = await state.http_client.send_scan(
                scan.direction, token, scan.device_id, scan.scanned_at
            )
            body = response.get("body", {}) if isinstance(response, dict) else {}
            reason = body.get("reason")
            allowed = body.get("allowed")
            logger.info(
                "[%s] device=%s token=%s status=%s reason=%s",
                scan.direction.upper(),
                scan.device_id,
                mask_token(token),
                response.get("status"),
                reason,
            )
            if allowed and body.get("open_door"):
                duration = body.get("door_open_duration") or 0
                user = body.get("user") or {}
                logger.info(
                    "Opening door device=%s duration=%ss user=%s",
                    scan.device_id,
                    duration,
                    user.get("email") or user.get("name") or "unknown",
                )
                if state.relay:
                    asyncio.create_task(state.relay.open(int(duration)))
                else:
                    logger.warning("Relay not configured; skipping door open.")
        except Exception as exc:
            logger.error(
                "Failed to send scan %s from %s: %s",
                scan.direction,
                scan.device_id,
                exc,
                exc_info=True,
            )
        finally:
            state.queue.task_done()


async def start_readers(state: ScannerState):
    readers = []
    tasks = []

    if state.config.scanner_in_mode.lower() == "hid":
        readers.append(
            HIDScannerReader(
                state.config.scanner_in_device, "in", state.config.device_id_in, state.queue
            )
        )
    else:
        readers.append(
            SerialScannerReader(
                state.config.scanner_in_device, "in", state.config.device_id_in, state.queue
            )
        )

    if state.config.scanner_out_mode.lower() == "hid":
        readers.append(
            HIDScannerReader(
                state.config.scanner_out_device, "out", state.config.device_id_out, state.queue
            )
        )
    else:
        readers.append(
            SerialScannerReader(
                state.config.scanner_out_device, "out", state.config.device_id_out, state.queue
            )
        )

    for reader in readers:
        tasks.append(asyncio.create_task(reader.run()))

    processor_task = asyncio.create_task(process_queue(state))
    tasks.append(processor_task)

    return tasks


async def shutdown(tasks):
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    config = ScannerConfig.from_env()
    setup_logging(config.log_path, config.log_level)
    relay = RelayController(pin=config.relay_gpio_pin, active_low=config.relay_active_low)

    http_client = ScannerHttpClient(
        base_url=config.backend_base_url,
        api_key=config.api_key,
        timeout=config.request_timeout,
        retry_attempts=config.retry_attempts,
        retry_backoff=config.retry_backoff,
    )
    queue: asyncio.Queue = asyncio.Queue()
    state = ScannerState(config=config, http_client=http_client, queue=queue, relay=relay)

    tasks = await start_readers(state)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    loop.add_signal_handler(signal.SIGINT, _signal_handler)

    await stop_event.wait()
    await shutdown(tasks)
    await http_client.aclose()
    if relay:
        relay.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
