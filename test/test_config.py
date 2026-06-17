"""Characterization tests for the existing Config.get() flow.

These lock in current behavior (env -> secretsmanager -> default, required
handling, typed coercion) so the nexus source can be added without changing
any existing semantics. Secrets Manager is stubbed at the
get_secretsmanager_secret boundary; no AWS calls are made.
"""

import os
import unittest
from unittest import mock

from gconfig import Config
from gconfig import exceptions


class CurrentBehaviorTests(unittest.TestCase):
    def test_env_wins_over_secretsmanager(self):
        sm = mock.MagicMock(return_value="from-sm")
        with mock.patch.dict(os.environ, {"GCONFIG_TEST_KEY": "from-env"}, clear=True):
            cfg = Config()
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.string(env="GCONFIG_TEST_KEY", secretsmanager="GCONFIG_TEST_KEY")
        self.assertEqual(result, "from-env")
        sm.assert_not_called()

    def test_secretsmanager_used_when_env_missing(self):
        sm = mock.MagicMock(return_value="from-sm")
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.string(env="GCONFIG_TEST_MISSING", secretsmanager="GCONFIG_TEST_KEY")
        self.assertEqual(result, "from-sm")
        sm.assert_called_once_with("GCONFIG_TEST_KEY", secretsmanager_prefix=None)

    def test_secretsmanager_error_falls_back_to_default(self):
        sm = mock.MagicMock(side_effect=RuntimeError("sm-down"))
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.string(secretsmanager="GCONFIG_TEST_KEY", default="fallback")
        self.assertEqual(result, "fallback")

    def test_secretsmanager_error_not_required_returns_none(self):
        sm = mock.MagicMock(side_effect=RuntimeError("sm-down"))
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                result = cfg.string(secretsmanager="GCONFIG_TEST_KEY")
        self.assertIsNone(result)

    def test_secretsmanager_error_required_no_default_raises_original(self):
        sm = mock.MagicMock(side_effect=RuntimeError("sm-down"))
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            with mock.patch.object(cfg, "get_secretsmanager_secret", sm):
                with self.assertRaises(RuntimeError):
                    cfg.string(secretsmanager="GCONFIG_TEST_KEY", required=True)

    def test_default_used_when_no_source_set(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            result = cfg.string(env="GCONFIG_TEST_MISSING", default="fallback")
        self.assertEqual(result, "fallback")

    def test_required_raises_when_nothing_found(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            with self.assertRaises(exceptions.RequiredSecretNotFoundException):
                cfg.string(env="GCONFIG_TEST_MISSING", required=True)

    def test_not_found_fn_called_instead_of_raising(self):
        calls = []
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config(not_found_fn=lambda args: calls.append(args))
            result = cfg.string(env="GCONFIG_TEST_MISSING", required=True)
        self.assertIsNone(result)
        self.assertEqual(len(calls), 1)

    def test_integer_coercion_from_env(self):
        with mock.patch.dict(os.environ, {"GCONFIG_TEST_PORT": "6379"}, clear=True):
            cfg = Config()
            result = cfg.integer(env="GCONFIG_TEST_PORT")
        self.assertEqual(result, 6379)
        self.assertIsInstance(result, int)

    def test_float_coercion_from_env(self):
        with mock.patch.dict(os.environ, {"GCONFIG_TEST_RATIO": "1.5"}, clear=True):
            cfg = Config()
            result = cfg.float(env="GCONFIG_TEST_RATIO")
        self.assertEqual(result, 1.5)

    def test_boolean_coercion_from_env(self):
        with mock.patch.dict(os.environ, {"GCONFIG_TEST_FLAG": "true"}, clear=True):
            cfg = Config()
            result = cfg.boolean(env="GCONFIG_TEST_FLAG")
        self.assertIs(result, True)

    def test_typed_default_passthrough(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            self.assertEqual(cfg.integer(env="GCONFIG_TEST_MISSING", default=6379), 6379)
            self.assertIs(cfg.boolean(env="GCONFIG_TEST_MISSING", default=True), True)


if __name__ == "__main__":
    unittest.main()
