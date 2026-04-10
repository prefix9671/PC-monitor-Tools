import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from collectors.libre_hardware_monitor import (
    LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
    read_cpu_core_max_temperature_sample,
)


DEFAULT_STATE_DIR = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "PC-monitor-Tools" / "temperature-monitor"
DEFAULT_STATE_PATH = DEFAULT_STATE_DIR / "cpu-core-temp-state.json"


def build_state_payload() -> Optional[dict[str, Any]]:
    sample = read_cpu_core_max_temperature_sample()
    if sample is None:
        return None

    now = time.time()
    return {
        "status": "ok",
        "provider_name": LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
        "value_c": round(sample.value_c, 1),
        "detail": sample.detail,
        "sensor_name": sample.sensor_name,
        "hardware_name": sample.hardware_name,
        "sampled_at_epoch": now,
        "sampled_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "pid": os.getpid(),
    }


def load_state_payload(state_path: Path) -> Optional[dict[str, Any]]:
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_state_payload(state_path: Path, payload: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp_path, state_path)


def capture_and_write_state(state_path: Path) -> bool:
    payload = build_state_payload()
    if payload is not None:
        write_state_payload(state_path, payload)
        return True

    existing_payload = load_state_payload(state_path)
    if existing_payload and existing_payload.get("status") == "ok":
        return False

    unavailable_payload = {
        "status": "unavailable",
        "provider_name": LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
        "sampled_at_epoch": time.time(),
        "sampled_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "pid": os.getpid(),
    }
    write_state_payload(state_path, unavailable_payload)
    return False


def run_worker_loop(state_path: Path, interval_sec: float, max_iterations: Optional[int] = None) -> int:
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        try:
            capture_and_write_state(state_path)
        except Exception as exc:
            existing_payload = load_state_payload(state_path) or {}
            if existing_payload.get("status") != "ok":
                write_state_payload(
                    state_path,
                    {
                        "status": "error",
                        "provider_name": LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
                        "error": str(exc),
                        "sampled_at_epoch": time.time(),
                        "sampled_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                        "pid": os.getpid(),
                    },
                )
        iteration += 1
        if max_iterations is not None and iteration >= max_iterations:
            break
        time.sleep(max(0.0, interval_sec))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Background CPU core temperature worker")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="JSON state file path")
    parser.add_argument("--interval-sec", type=float, default=30.0, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Capture one sample and exit")
    parser.add_argument("--max-iterations", type=int, default=None, help="Internal test hook")

    args = parser.parse_args(argv)

    if args.once:
        try:
            capture_and_write_state(args.state_path)
            return 0
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1

    return run_worker_loop(
        state_path=args.state_path,
        interval_sec=args.interval_sec,
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    sys.exit(main())
