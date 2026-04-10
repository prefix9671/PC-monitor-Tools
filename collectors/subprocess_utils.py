import locale
import subprocess
from typing import Any


_FALLBACK_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp949",
    "euc-kr",
)


def decode_subprocess_text(payload: bytes | str | None) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload

    preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
    encodings = []
    seen = set()
    for encoding in (preferred_encoding, *_FALLBACK_ENCODINGS):
        normalized = encoding.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        encodings.append(encoding)

    for encoding in encodings:
        try:
            return payload.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    return payload.decode(preferred_encoding, errors="replace")


def run_text_capture(*popenargs: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    run_kwargs = dict(kwargs)
    run_kwargs.pop("capture_output", None)
    run_kwargs.pop("text", None)
    run_kwargs.pop("encoding", None)
    run_kwargs.pop("errors", None)
    run_kwargs.pop("check", None)

    completed = subprocess.run(
        *popenargs,
        capture_output=True,
        text=False,
        check=False,
        **run_kwargs,
    )
    return subprocess.CompletedProcess(
        completed.args,
        completed.returncode,
        decode_subprocess_text(completed.stdout).strip(),
        decode_subprocess_text(completed.stderr).strip(),
    )


def check_output_text(*popenargs: Any, **kwargs: Any) -> str:
    output_kwargs = dict(kwargs)
    output_kwargs.pop("text", None)
    output_kwargs.pop("encoding", None)
    output_kwargs.pop("errors", None)

    payload = subprocess.check_output(
        *popenargs,
        text=False,
        **output_kwargs,
    )
    return decode_subprocess_text(payload)
