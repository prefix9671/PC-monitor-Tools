import argparse
import fnmatch
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


RULES_PATH = Path(__file__).with_name("doc_sync_rules.toml")


@dataclass(frozen=True)
class DocSyncRule:
    name: str
    trigger_prefixes: tuple[str, ...]
    required_docs: tuple[str, ...]


@dataclass(frozen=True)
class DocSyncConfig:
    doc_prefix: str
    generated_prefixes: tuple[str, ...]
    ignored_globs: tuple[str, ...]
    code_change_exempt_prefixes: tuple[str, ...]
    baseline_required_docs: tuple[str, ...]
    rules: tuple[DocSyncRule, ...]


def _normalize_path(path: str) -> str:
    normalized = path.strip().strip('"')
    return normalized.replace("\\", "/")


def load_rule_config(path: Path | None = None) -> DocSyncConfig:
    config_path = path or RULES_PATH
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    meta = raw["meta"]
    raw_rules = raw["rules"]
    return DocSyncConfig(
        doc_prefix=_normalize_path(meta["doc_prefix"]),
        generated_prefixes=tuple(_normalize_path(prefix) for prefix in meta["generated_prefixes"]),
        ignored_globs=tuple(_normalize_path(pattern) for pattern in meta.get("ignored_globs", [])),
        code_change_exempt_prefixes=tuple(
            _normalize_path(prefix) for prefix in meta["code_change_exempt_prefixes"]
        ),
        baseline_required_docs=tuple(_normalize_path(doc) for doc in meta["baseline_required_docs"]),
        rules=tuple(
            DocSyncRule(
                name=rule["name"],
                trigger_prefixes=tuple(_normalize_path(prefix) for prefix in rule["trigger_prefixes"]),
                required_docs=tuple(_normalize_path(doc) for doc in rule["required_docs"]),
            )
            for rule in raw_rules
        ),
    )


def _run_git(*args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git command failed")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _looks_like_changed(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes)


def _matches_ignored_glob(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _is_ignored_path(path: str, config: DocSyncConfig) -> bool:
    return _matches_ignored_glob(path, config.ignored_globs)


def _is_generated_path(path: str, config: DocSyncConfig) -> bool:
    return _looks_like_changed(path, config.generated_prefixes)


def _is_non_doc_change(path: str, config: DocSyncConfig) -> bool:
    return not path.startswith(config.doc_prefix) and not _is_generated_path(path, config)


def collect_changed_files(base_ref: str | None) -> list[str]:
    if base_ref:
        try:
            _run_git("rev-parse", "--verify", base_ref)
        except RuntimeError as exc:
            raise RuntimeError(f"base ref '{base_ref}' could not be resolved: {exc}") from exc
        tracked = _run_git("diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...HEAD")
    else:
        tracked = _run_git("diff", "--name-only", "--diff-filter=ACMR", "HEAD")

    untracked = _run_git("ls-files", "--others", "--exclude-standard")
    return sorted({_normalize_path(path) for path in [*tracked, *untracked]})


def evaluate_changed_files(changed_files: list[str], config: DocSyncConfig | None = None) -> list[str]:
    active_config = config or load_rule_config()
    changed_set = {
        _normalize_path(path)
        for path in changed_files
        if not _is_ignored_path(_normalize_path(path), active_config)
    }
    missing_messages = []

    for rule in active_config.rules:
        matched = [path for path in sorted(changed_set) if _looks_like_changed(path, rule.trigger_prefixes)]
        if not matched:
            continue

        missing_docs = [doc for doc in rule.required_docs if doc not in changed_set]
        if missing_docs:
            missing_messages.append(
                f"- Rule '{rule.name}' triggered by {', '.join(matched)}: update {', '.join(missing_docs)}"
            )

    relevant_code_changes = [
        path
        for path in sorted(changed_set)
        if _is_non_doc_change(path, active_config)
        and not _looks_like_changed(path, active_config.code_change_exempt_prefixes)
    ]
    if relevant_code_changes:
        missing_docs = [doc for doc in active_config.baseline_required_docs if doc not in changed_set]
        if missing_docs:
            missing_messages.append(
                "- Baseline docs rule triggered by "
                f"{', '.join(relevant_code_changes)}: update {', '.join(missing_docs)}"
            )

    return missing_messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify that code changes are accompanied by the expected active docs.")
    parser.add_argument("--base-ref", help="Git base ref to compare against, for example origin/main")
    args = parser.parse_args()

    try:
        config = load_rule_config()
        changed_files = [
            path
            for path in collect_changed_files(args.base_ref)
            if not _is_ignored_path(path, config)
        ]
    except (KeyError, RuntimeError, tomllib.TOMLDecodeError, OSError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    if not changed_files:
        print("[OK] No changed files detected for docs sync verification.")
        return 0

    changed_set = {_normalize_path(path) for path in changed_files}
    missing_messages = evaluate_changed_files(changed_files, config=config)

    if missing_messages:
        print("[ERROR] Active docs look out of sync with the current code changes.")
        for message in missing_messages:
            print(message)
        return 1

    print("[OK] Active docs changed alongside the relevant code paths.")
    for path in sorted(changed_set):
        if path.startswith(config.doc_prefix):
            print(f"  docs: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
