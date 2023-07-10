import unittest

from . import gconfig

class ConfigInitTests(unittest.TestCase):
    def config_aws_creds_missing(self):
        with self.assertRaises(Exception):
            config = gconfig.Config(namespace='test')
            config.string(env='REDIS_URL', secretsmanager='REDIS_URL', required=True)


if __name__ == "__main__":
    unittest.main()
