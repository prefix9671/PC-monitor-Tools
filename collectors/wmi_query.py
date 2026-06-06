from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Iterable, Optional


_SYSTEM_MANAGEMENT_LOCK = threading.Lock()
_SYSTEM_MANAGEMENT_READY = False
_SYSTEM_MANAGEMENT_IMPORTS: dict[str, Any] = {}


@dataclass(frozen=True)
class WmiQuerySpec:
    namespace: str
    class_name: str
    properties: tuple[str, ...]
    where: Optional[str] = None


def _ensure_system_management() -> dict[str, Any]:
    global _SYSTEM_MANAGEMENT_READY

    if _SYSTEM_MANAGEMENT_READY:
        return _SYSTEM_MANAGEMENT_IMPORTS

    with _SYSTEM_MANAGEMENT_LOCK:
        if _SYSTEM_MANAGEMENT_READY:
            return _SYSTEM_MANAGEMENT_IMPORTS

        import clr

        clr.AddReference("System.Management")

        from System import TimeSpan
        from System.Management import ManagementClass, ManagementObjectSearcher, ManagementPath, ManagementScope, ObjectQuery

        _SYSTEM_MANAGEMENT_IMPORTS.update(
            {
                "ManagementClass": ManagementClass,
                "ManagementObjectSearcher": ManagementObjectSearcher,
                "ManagementPath": ManagementPath,
                "ManagementScope": ManagementScope,
                "ObjectQuery": ObjectQuery,
                "TimeSpan": TimeSpan,
            }
        )
        _SYSTEM_MANAGEMENT_READY = True
        return _SYSTEM_MANAGEMENT_IMPORTS


def _normalize_namespace(namespace: str) -> str:
    normalized = namespace.strip().replace("/", "\\")
    if normalized.startswith("\\\\"):
        return normalized
    if normalized.startswith("root\\"):
        return f"\\\\.\\{normalized}"
    return f"\\\\.\\root\\{normalized}"


def _quote_property(property_name: str) -> str:
    return property_name.strip()


def _build_wql(spec: WmiQuerySpec) -> str:
    fields = ", ".join(_quote_property(prop) for prop in spec.properties) if spec.properties else "*"
    query = f"SELECT {fields} FROM {spec.class_name}"
    if spec.where:
        query += f" WHERE {spec.where}"
    return query


def _to_python_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value

    try:
        if hasattr(value, "GetType") and value.GetType().IsArray:
            return [_to_python_value(item) for item in value]
    except Exception:
        pass

    try:
        return int(value)
    except Exception:
        pass

    try:
        return float(value)
    except Exception:
        pass

    try:
        return str(value)
    except Exception:
        return repr(value)


def query_wmi_records(spec: WmiQuerySpec, timeout_sec: float = 2.0) -> list[dict[str, Any]]:
    try:
        imports = _ensure_system_management()
        scope = imports["ManagementScope"](_normalize_namespace(spec.namespace))
        scope.Connect()
        searcher = imports["ManagementObjectSearcher"](scope, imports["ObjectQuery"](_build_wql(spec)))
        if timeout_sec and timeout_sec > 0:
            searcher.Options.Timeout = imports["TimeSpan"].FromSeconds(float(timeout_sec))

        records: list[dict[str, Any]] = []
        for item in searcher.Get():
            record = {}
            for prop in spec.properties:
                try:
                    value = item.GetPropertyValue(prop)
                except Exception:
                    value = None
                record[prop] = _to_python_value(value)
            records.append(record)
        return records
    except Exception:
        return []


def wmi_class_available(namespace: str, class_name: str, timeout_sec: float = 2.0) -> bool:
    try:
        imports = _ensure_system_management()
        scope = imports["ManagementScope"](_normalize_namespace(namespace))
        scope.Connect()
        path = imports["ManagementPath"](class_name)
        management_class = imports["ManagementClass"](scope, path, None)
        if timeout_sec and timeout_sec > 0:
            management_class.Options.Timeout = imports["TimeSpan"].FromSeconds(float(timeout_sec))
        management_class.Get()
        return True
    except Exception:
        return False


def sum_numeric_property(records: Iterable[dict[str, Any]], property_name: str) -> Optional[float]:
    total = 0.0
    found = False
    for record in records:
        try:
            total += float(record.get(property_name))
            found = True
        except (TypeError, ValueError):
            continue
    return total if found else None
