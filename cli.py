import argparse
import sys

import config
from collectors.core import MonitorEngine
from collectors.cpu_temperature import CpuTemperatureProbe
from collectors.dell_command_monitor import ensure_dcm_ready
from collectors.pawnio_package import (
    ensure_pawnio_setup_path,
    install_pawnio,
    is_current_process_elevated,
    read_pawnio_installed_version,
)


def _prepare_temperature_provider():
    result = ensure_dcm_ready(auto_install=True)
    if result.message:
        print(result.message)
    return result


def _handle_install_pawnio(args):
    installed_version = read_pawnio_installed_version()
    if args.check_only:
        if installed_version:
            print(f"PawnIO installed: {installed_version}")
            sys.exit(0)
        print("PawnIO is not installed.")
        sys.exit(2)

    if installed_version and not args.force:
        print(f"PawnIO is already installed: {installed_version}")
        sys.exit(0)

    try:
        setup_path = ensure_pawnio_setup_path()
    except Exception as exc:
        print(f"PawnIO setup package is not available: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"PawnIO setup package: {setup_path}")
    elevated = is_current_process_elevated()
    if elevated is False:
        print("Administrator privileges are required to install the PawnIO driver.", file=sys.stderr)

    result = install_pawnio(setup_path=setup_path)
    if result.ok:
        if result.installed_version:
            print(f"PawnIO installed: {result.installed_version}")
        else:
            print("PawnIO setup completed.")
        if result.reboot_required:
            print("PawnIO setup reported that a reboot is required.")
        sys.exit(0)

    if result.error:
        print(f"PawnIO setup failed: {result.error}", file=sys.stderr)
    else:
        print(f"PawnIO setup failed with exit code {result.returncode}.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="System Resource Monitor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    start_parser = subparsers.add_parser("start", help="Start the collector")
    start_parser.add_argument("--out-dir", type=str, default=config.OUTPUT_DIR, help="Output directory for logs")
    start_parser.add_argument(
        "--interval",
        type=int,
        default=config.SAMPLE_INTERVAL_SEC,
        help="Sampling interval in seconds",
    )
    start_parser.add_argument(
        "--window",
        type=int,
        default=config.AGGREGATION_WINDOW_SEC,
        help="Aggregation window in seconds",
    )
    start_parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Stop after N sampling iterations (for testing)",
    )

    probe_temp_parser = subparsers.add_parser("probe-temp", help="Probe CPU temperature sensor availability")
    probe_temp_parser.add_argument(
        "--retry-interval",
        type=float,
        default=0.0,
        help="Retry interval in seconds for sensor detection",
    )

    install_pawnio_parser = subparsers.add_parser("install-pawnio", help="Install the bundled PawnIO driver package")
    install_pawnio_parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check whether PawnIO is installed",
    )
    install_pawnio_parser.add_argument(
        "--force",
        action="store_true",
        help="Run the PawnIO installer even when a version is already installed",
    )

    args = parser.parse_args()

    if args.command == "start":
        _prepare_temperature_provider()
        engine = MonitorEngine(
            output_dir=args.out_dir,
            interval_sec=args.interval,
            window_sec=args.window,
        )
        engine.run(max_iterations=args.iterations)
    elif args.command == "probe-temp":
        _prepare_temperature_provider()
        probe = CpuTemperatureProbe(retry_interval_sec=args.retry_interval)
        value = probe.read_celsius(force_refresh=True)
        source = probe.source_name or "Unavailable"
        sensor_detail = probe.source_detail
        if value is None:
            print(f"CPU temperature sensor not available. Source: {source}")
            if sensor_detail:
                print(f"Sensor: {sensor_detail}")
            sys.exit(1)
        print(f"CPU temperature: {value:.1f}C (Source: {source})")
        if sensor_detail:
            print(f"Sensor: {sensor_detail}")
    elif args.command == "install-pawnio":
        _handle_install_pawnio(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
