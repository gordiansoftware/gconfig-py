import logging

from .cache import Cache, CacheEntry
from .config import Config
from .exceptions import (
    AWSInvalidCredentialsException,
    AWSInvalidSessionException,
    AWSMissingAccessKeyIdException,
    AWSMissingRegionException,
    AWSMissingRoleARNException,
    AWSMissingRoleSessionNameException,
    AWSMissingSecretAccessKeyException,
    AWSMissingSessionTokenException,
)
from .parse import parse_entry

# Attach a no-op handler to gconfig's top-level logger so library log records
# (e.g. nexus read failures) don't print to stderr in consumers that haven't
# configured logging. Apps that configure logging still receive them via
# propagation.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "AWSInvalidCredentialsException",
    "AWSInvalidSessionException",
    "AWSMissingAccessKeyIdException",
    "AWSMissingRegionException",
    "AWSMissingRoleARNException",
    "AWSMissingRoleSessionNameException",
    "AWSMissingSecretAccessKeyException",
    "AWSMissingSessionTokenException",
    "Cache",
    "CacheEntry",
    "Config",
    "parse_entry",
]

__version__ = "0.3.0"
