import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))

from collectors.wmi_query import (
    WmiQuerySpec,
    _build_wql,
    _normalize_namespace,
    sum_numeric_property,
    wmi_class_available,
)


class TestWmiQuery(unittest.TestCase):
    def test_normalize_namespace_adds_local_machine_prefix(self):
        self.assertEqual(r"\\.\root\cimv2", _normalize_namespace(r"root\cimv2"))
        self.assertEqual(r"\\.\root\wmi", _normalize_namespace(r"wmi"))
        self.assertEqual(r"\\remote\root\cimv2", _normalize_namespace(r"\\remote\root\cimv2"))

    def test_build_wql_with_fields_and_where_clause(self):
        spec = WmiQuerySpec(
            namespace=r"root\cimv2",
            class_name="Win32_ComputerSystem",
            properties=("Manufacturer", "Model"),
            where="Manufacturer IS NOT NULL",
        )

        self.assertEqual(
            "SELECT Manufacturer, Model FROM Win32_ComputerSystem WHERE Manufacturer IS NOT NULL",
            _build_wql(spec),
        )

    def test_sum_numeric_property_ignores_missing_or_invalid_values(self):
        total = sum_numeric_property(
            [
                {"Capacity": "1024"},
                {"Capacity": 2048},
                {"Capacity": None},
                {"Capacity": "bad"},
            ],
            "Capacity",
        )

        self.assertEqual(3072.0, total)

    def test_query_errors_return_empty_records(self):
        import collectors.wmi_query as wmi_query

        with patch.object(wmi_query, "_ensure_system_management", side_effect=RuntimeError("boom")):
            self.assertEqual([], wmi_query.query_wmi_records(WmiQuerySpec("root\\cimv2", "Bad", ("Name",))))

    def test_wmi_class_available_loads_management_class(self):
        import collectors.wmi_query as wmi_query

        class FakeScope:
            def __init__(self, namespace):
                self.namespace = namespace
                self.connected = False

            def Connect(self):
                self.connected = True

        class FakePath:
            def __init__(self, class_name):
                self.class_name = class_name

        class FakeOptions:
            Timeout = None

        class FakeManagementClass:
            last_instance = None

            def __init__(self, scope, path, options):
                self.scope = scope
                self.path = path
                self.options = options
                self.Options = FakeOptions()
                self.loaded = False
                FakeManagementClass.last_instance = self

            def Get(self):
                self.loaded = True

        class FakeTimeSpan:
            @staticmethod
            def FromSeconds(seconds):
                return ("seconds", seconds)

        imports = {
            "ManagementScope": FakeScope,
            "ManagementPath": FakePath,
            "ManagementClass": FakeManagementClass,
            "TimeSpan": FakeTimeSpan,
        }

        with patch.object(wmi_query, "_ensure_system_management", return_value=imports):
            self.assertTrue(wmi_class_available("root\\cimv2", "Win32_ComputerSystem", timeout_sec=1.5))

        instance = FakeManagementClass.last_instance
        self.assertEqual(r"\\.\root\cimv2", instance.scope.namespace)
        self.assertTrue(instance.scope.connected)
        self.assertEqual("Win32_ComputerSystem", instance.path.class_name)
        self.assertEqual(("seconds", 1.5), instance.Options.Timeout)
        self.assertTrue(instance.loaded)

    def test_wmi_class_available_returns_false_on_load_error(self):
        import collectors.wmi_query as wmi_query

        class FakeScope:
            def __init__(self, namespace):
                self.namespace = namespace

            def Connect(self):
                pass

        class FakePath:
            def __init__(self, class_name):
                self.class_name = class_name

        class FailingManagementClass:
            def __init__(self, scope, path, options):
                pass

            def Get(self):
                raise RuntimeError("missing")

        imports = {
            "ManagementScope": FakeScope,
            "ManagementPath": FakePath,
            "ManagementClass": FailingManagementClass,
        }

        with patch.object(wmi_query, "_ensure_system_management", return_value=imports):
            self.assertFalse(wmi_class_available("root\\cimv2", "Missing_Class", timeout_sec=0))


if __name__ == "__main__":
    unittest.main()
