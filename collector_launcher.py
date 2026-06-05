from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


SW_SHOWNORMAL = 1

SHELL_EXECUTE_ERRORS = {
    0: "시스템 메모리 또는 리소스가 부족합니다.",
    2: "실행 파일을 찾을 수 없습니다.",
    3: "실행 경로를 찾을 수 없습니다.",
    5: "액세스가 거부되었습니다. UAC 거부, Windows 보안 정책, 파일 차단 여부를 확인하세요.",
    8: "메모리가 부족해 프로세스를 시작하지 못했습니다.",
    26: "파일 공유 위반으로 프로세스를 시작하지 못했습니다.",
    27: "파일 연결 정보가 불완전합니다.",
    28: "DDE 요청 시간이 초과되었습니다.",
    29: "DDE 요청이 실패했습니다.",
    30: "DDE 요청이 처리 중이라 시작하지 못했습니다.",
    31: "지정한 파일을 실행할 연결 프로그램이 없습니다.",
    32: "필요한 DLL을 찾을 수 없습니다.",
}


@dataclass(frozen=True)
class CollectorLaunchSpec:
    executable: str
    arguments: tuple[str, ...]
    cwd: str


@dataclass(frozen=True)
class CollectorLaunchResult:
    ok: bool
    message: str
    detail: str = ""
    used_elevation: bool = False


class CollectorLaunchError(RuntimeError):
    pass


def resolve_collector_launch_spec() -> CollectorLaunchSpec:
    if getattr(sys, "frozen", False):
        executable = sys.executable
        arguments = ("start",)
        cwd = str(Path(sys.executable).resolve().parent)
    else:
        repo_dir = Path(__file__).resolve().parent
        executable = sys.executable
        arguments = (str(repo_dir / "cli.py"), "start")
        cwd = str(repo_dir)

    return CollectorLaunchSpec(executable=executable, arguments=arguments, cwd=cwd)


def is_current_process_admin() -> bool:
    if os.name != "nt":
        return hasattr(os, "geteuid") and os.geteuid() == 0

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _format_command_for_display(spec: CollectorLaunchSpec) -> str:
    command = [spec.executable, *spec.arguments]
    return subprocess.list2cmdline(command)


def _format_shell_execute_error(code: int, spec: CollectorLaunchSpec) -> str:
    message = SHELL_EXECUTE_ERRORS.get(code, f"Windows ShellExecute 오류 코드 {code}입니다.")
    return f"{message} 실행 명령: {_format_command_for_display(spec)}"


def _launch_direct(spec: CollectorLaunchSpec, popen: Callable[..., object] = subprocess.Popen) -> None:
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    popen(
        [spec.executable, *spec.arguments],
        cwd=spec.cwd,
        creationflags=creationflags,
    )


def _launch_elevated(
    spec: CollectorLaunchSpec,
    shell_execute: Callable[..., int] | None = None,
) -> None:
    if os.name != "nt":
        raise CollectorLaunchError("관리자 권한 상승 실행은 Windows에서만 지원됩니다.")

    shell_execute = shell_execute or ctypes.windll.shell32.ShellExecuteW
    result = int(
        shell_execute(
            None,
            "runas",
            spec.executable,
            subprocess.list2cmdline(spec.arguments),
            spec.cwd,
            SW_SHOWNORMAL,
        )
    )

    if result <= 32:
        raise CollectorLaunchError(_format_shell_execute_error(result, spec))


def launch_collector_from_current_process(
    admin_checker: Callable[[], bool] = is_current_process_admin,
    popen: Callable[..., object] = subprocess.Popen,
    shell_execute: Callable[..., int] | None = None,
) -> CollectorLaunchResult:
    spec = resolve_collector_launch_spec()

    try:
        if admin_checker():
            _launch_direct(spec, popen=popen)
            return CollectorLaunchResult(
                ok=True,
                message="현재 앱이 관리자 권한이므로 수집기를 바로 시작했습니다.",
                detail="명령 프롬프트 창이 열리며, 창을 닫으면 모니터링이 종료됩니다.",
                used_elevation=False,
            )

        _launch_elevated(spec, shell_execute=shell_execute)
        return CollectorLaunchResult(
            ok=True,
            message="Windows 관리자 권한 요청을 보냈습니다.",
            detail="UAC 허용 뒤 명령 프롬프트 창이 열리며, 창을 닫으면 모니터링이 종료됩니다.",
            used_elevation=True,
        )
    except CollectorLaunchError as exc:
        return CollectorLaunchResult(
            ok=False,
            message="모니터링 시작 요청이 Windows에서 차단되었습니다.",
            detail=str(exc),
            used_elevation=True,
        )
    except Exception as exc:
        return CollectorLaunchResult(
            ok=False,
            message="모니터링 시작 중 예기치 않은 오류가 발생했습니다.",
            detail=f"{type(exc).__name__}: {exc}",
            used_elevation=False,
        )
