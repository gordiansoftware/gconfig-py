class AWSMissingAccessKeyIdException(ValueError):
    """Raised when AWS_ACCESS_KEY_ID not found in the environment variables."""

    pass


class AWSMissingSecretAccessKeyException(ValueError):
    """Raised when AWS_SECRET_ACCESS_KEY not found in the environment variables."""

    pass


class AWSMissingRegionException(ValueError):
    """Raised when AWS_REGION not found in the environment variables."""

    pass


class AWSMissingRoleARNException(ValueError):
    """Raised when AWS_ROLE_ARN is not provided."""

    pass

class AWSMissingRoleSessionNameException(ValueError):
    """Raised when AWS_ROLE_SESSION_NAME is not provided."""

    pass


class AWSMissingSessionTokenException(ValueError):
    """Raised when AWS_SESSION_TOKEN not found in the environment variables."""

    pass


class AWSInvalidCredentialsException(ValueError):
    """Raised when invalid credentials are provided to the Config class."""

    pass


class AWSInvalidSessionException(ValueError):
    """Raised when a boto3.Session is not provided to the Config class."""

    pass


class RequiredSecretNotFoundException(KeyError):
    """Raised when a required secret is not found in the environment variables or Secrets Manager."""

    pass
