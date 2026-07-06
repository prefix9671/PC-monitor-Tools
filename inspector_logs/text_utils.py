from __future__ import annotations


def _has_utf16_bom(raw_bytes: bytes) -> bool:
    return raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff"))


def _looks_like_utf16(raw_bytes: bytes) -> str | None:
    sample = raw_bytes[:4096]
    if len(sample) < 4:
        return None

    even_nulls = sample[0::2].count(0)
    odd_nulls = sample[1::2].count(0)
    pair_count = max(len(sample) // 2, 1)

    if odd_nulls / pair_count > 0.35 and odd_nulls > even_nulls * 4:
        return "utf-16-le"
    if even_nulls / pair_count > 0.35 and even_nulls > odd_nulls * 4:
        return "utf-16-be"
    return None


def decode_text(raw_bytes: bytes) -> str:
    if not raw_bytes:
        return ""

    if _has_utf16_bom(raw_bytes):
        return raw_bytes.decode("utf-16", errors="replace")

    utf16_encoding = _looks_like_utf16(raw_bytes)
    if utf16_encoding is not None:
        return raw_bytes.decode(utf16_encoding, errors="replace")

    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        if text.count("\x00") / max(len(text), 1) < 0.05:
            return text

    return raw_bytes.decode("latin-1", errors="ignore")


def decode_text_lines(raw_bytes: bytes) -> list[str]:
    return decode_text(raw_bytes).splitlines()
