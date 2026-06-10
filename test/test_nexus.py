"""Tests for the nexus source in Config.get().

The nexus client is duck-typed and injected via Config(nexus_client=...);
the fakes below stand in for nexus_client_py's ConfigsClient/ConfigValue so
no grpc stack is needed. Read order under test:
env -> nexus -> secretsmanager -> default.
"""

import os
import unittest
from unittest import mock

from gconfig import Config
from gconfig import exceptions


class FakeConfigValue:
    def __init__(self, value, redacted=False):
        self._value = value
        self.is_redacted = redacted

    def as_string(self):
        return self._value


class FakeNexusClient:
    """Duck-typed stand-in for nexus_client_py's ConfigsClient."""

    def __init__(self, values=None, error=None):
        self.values = values or {}
        self.error = error
        self.calls = []

    def get(self, key):
        self.calls.append(key)
        if self.error is not None:
            raise self.error
        if key not in self.values:
            raise KeyError(key)  # stands in for ConfigKeyNotFound
        return self.values[key]


class NexusSourceTests(unittest.TestCase):
    def test_nexus_value_wins_over_secretsmanager(self):
        nexus = FakeNexusClient(values={"TEST_KEY": FakeConfigValue("from-nexus")})
        sm = mock.MagicMock(return_value="from-sm")
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config(nexus_client=nexus)
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.get(
                    str,
                    env="GCONFIG_TEST_MISSING",
                    secretsmanager="TEST_KEY",
                    nexus="TEST_KEY",
                )
        self.assertEqual(result, "from-nexus")
        self.assertEqual(nexus.calls, ["TEST_KEY"])
        sm.assert_not_called()

    def test_nexus_error_falls_through_to_secretsmanager(self):
        nexus = FakeNexusClient(error=RuntimeError("nexus-down"))
        sm = mock.MagicMock(return_value="from-sm")
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config(nexus_client=nexus)
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.get(str, secretsmanager="TEST_KEY", nexus="TEST_KEY")
        self.assertEqual(result, "from-sm")
        self.assertEqual(nexus.calls, ["TEST_KEY"])

    def test_redacted_nexus_value_falls_through_to_secretsmanager(self):
        nexus = FakeNexusClient(
            values={"TEST_KEY": FakeConfigValue("<redacted>", redacted=True)}
        )
        sm = mock.MagicMock(return_value="from-sm")
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config(nexus_client=nexus)
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.get(str, secretsmanager="TEST_KEY", nexus="TEST_KEY")
        self.assertEqual(result, "from-sm")

    def test_kill_switch_skips_listed_keys(self):
        nexus = FakeNexusClient(
            values={
                "DISABLED_KEY": FakeConfigValue("from-nexus"),
                "ACTIVE_KEY": FakeConfigValue("from-nexus"),
            }
        )
        sm = mock.MagicMock(return_value="from-sm")
        with mock.patch.dict(
            os.environ,
            {"GCONFIG_NEXUS_DISABLED_KEYS": " DISABLED_KEY , OTHER_KEY "},
            clear=True,
        ):
            cfg = Config(nexus_client=nexus)
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                disabled = cfg.get(
                    str, secretsmanager="DISABLED_KEY", nexus="DISABLED_KEY"
                )
                active = cfg.get(str, secretsmanager="ACTIVE_KEY", nexus="ACTIVE_KEY")
        self.assertEqual(disabled, "from-sm")
        self.assertEqual(active, "from-nexus")
        self.assertEqual(nexus.calls, ["ACTIVE_KEY"])

    def test_nexus_kwarg_inert_when_no_client_injected(self):
        sm = mock.MagicMock(return_value="from-sm")
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.get(str, secretsmanager="TEST_KEY", nexus="TEST_KEY")
        self.assertEqual(result, "from-sm")

    def test_typed_accessors_coerce_nexus_values(self):
        nexus = FakeNexusClient(
            values={
                "PORT": FakeConfigValue("8080"),
                "FLAG": FakeConfigValue("true"),
                "RATIO": FakeConfigValue("1.5"),
                "NAME": FakeConfigValue("svc"),
            }
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config(nexus_client=nexus)
            self.assertEqual(cfg.integer(nexus="PORT"), 8080)
            self.assertIs(cfg.boolean(nexus="FLAG"), True)
            self.assertEqual(cfg.float(nexus="RATIO"), 1.5)
            self.assertEqual(cfg.string(nexus="NAME"), "svc")

    def test_env_wins_over_nexus(self):
        nexus = FakeNexusClient(values={"TEST_KEY": FakeConfigValue("from-nexus")})
        with mock.patch.dict(os.environ, {"GCONFIG_TEST_KEY": "from-env"}, clear=True):
            cfg = Config(nexus_client=nexus)
            result = cfg.get(str, env="GCONFIG_TEST_KEY", nexus="TEST_KEY")
        self.assertEqual(result, "from-env")
        self.assertEqual(nexus.calls, [])

    def test_nexus_error_no_secretsmanager_uses_default(self):
        nexus = FakeNexusClient(error=RuntimeError("nexus-down"))
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config(nexus_client=nexus)
            result = cfg.get(str, nexus="TEST_KEY", default="fallback")
        self.assertEqual(result, "fallback")

    def test_nexus_error_required_no_other_source_raises_required(self):
        nexus = FakeNexusClient(error=RuntimeError("nexus-down"))
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config(nexus_client=nexus)
            with self.assertRaises(exceptions.RequiredSecretNotFoundException):
                cfg.get(str, nexus="TEST_KEY", required=True)


if __name__ == "__main__":
    unittest.main()
