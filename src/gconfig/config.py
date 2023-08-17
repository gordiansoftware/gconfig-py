import os, boto3
from typing import Optional, Callable, Dict
from botocore.exceptions import ClientError

from . import exceptions, cache


class Config:
    def __init__(
        self,
        aws_prefix: str = "",
        secretsmanager_prefix: str = None,
        not_found_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        self.aws_prefix = aws_prefix
        self.secretsmanager_client = None
        self.secretsmanager_prefix = secretsmanager_prefix
        self.not_found_fn = not_found_fn
        self.cache_env = cache.Cache()
        self.cache_secretsmanager = cache.Cache()

    # Secrets Manager
    def get_secretsmanager(self) -> boto3.client:
        if self.secretsmanager_client is None:
            aws_access_key_id = os.environ.get(f"{self.aws_prefix}AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.environ.get(
                f"{self.aws_prefix}AWS_SECRET_ACCESS_KEY"
            )
            region_name = os.environ.get(f"{self.aws_prefix}AWS_REGION")

            if aws_access_key_id is None:
                raise exceptions.AWSMissingAccessKeyIdException

            if aws_secret_access_key is None:
                raise exceptions.AWSMissingSecretAccessKeyException

            if region_name is None:
                raise exceptions.AWSMissingRegionException

            # AWS_SESSION_TOKEN is optional, if not provided, assume role will be used.
            aws_session_token = os.environ.get(f"{self.aws_prefix}AWS_SESSION_TOKEN")

            # If AWS_SESSION_TOKEN is not provided, assume role.
            if aws_session_token is None:
                aws_role_arn = os.environ.get(f"{self.aws_prefix}AWS_ROLE_ARN")
                aws_role_session_name = os.environ.get(
                    f"{self.aws_prefix}AWS_ROLE_SESSION_NAME"
                )

                if aws_role_arn is None:
                    raise exceptions.AWSMissingRoleARNException

                if aws_role_session_name is None:
                    raise exceptions.AWSMissingRoleSessionNameException

                self.aws_role_arn = aws_role_arn
                self.aws_role_session_name = aws_role_session_name

                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )

                sts = session.client("sts")
                assumed_role_object = sts.assume_role(
                    RoleArn=self.aws_role_arn,
                    RoleSessionName=self.aws_role_session_name,
                )
                credentials = assumed_role_object.get("Credentials")

                # Override the credentials with the assumed role credentials.
                aws_access_key_id = credentials.get("AccessKeyId")
                aws_secret_access_key = credentials.get("SecretAccessKey")
                aws_session_token = credentials.get("SessionToken")

            # session token must be set now.
            if aws_session_token is None:
                raise exceptions.AWSMissingSessionTokenException

            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region_name=region_name,
            )

            self.session = session
            self.secretsmanager_client = self.session.client("secretsmanager")

        return self.secretsmanager_client

    def get_secretsmanager_key(self, secret_id) -> str:
        if self.secretsmanager_prefix is not None:
            secret_id = f"{self.secretsmanager_prefix}/{secret_id}"
        return secret_id

    def get_secretsmanager_secret(self, secret_id: str) -> str:
        secretsmanager_client = self.get_secretsmanager()
        response = secretsmanager_client.get_secret_value(
            SecretId=self.get_secretsmanager_key(secret_id)
        )
        return response.get("SecretString")

    def update_secretsmanager_secret(self, secret_id: str, secret: str) -> None:
        secretsmanager_client = self.get_secretsmanager()
        secretsmanager_client.put_secret_value(
            SecretId=self.get_secretsmanager_key(secret_id),
            SecretString=secret,
        )

    def get(
        self,
        env: str = None,
        secretsmanager: str = None,
        default: any = None,
        required: bool = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[str]:
        secret = os.environ.get(env) if env is not None else None
        if secret is not None:
            self.cache_env.set(
                cache.CacheEntry(
                    env,
                    secret,
                    change_callback_fn=change_callback_fn,
                ),
            )

        if secret is None and secretsmanager is not None:
            try:
                secret = self.get_secretsmanager_secret(secretsmanager)
                self.cache_secretsmanager.set(
                    cache.CacheEntry(
                        secretsmanager,
                        secret,
                        change_callback_fn=change_callback_fn,
                    ),
                )
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    secret = None
                else:
                    raise e
            except Exception as e:
                if not required or default is not None:
                    secret = default
                else:
                    raise e

        if secret is None and default is not None:
            secret = default

        if secret is None and required:
            if self.not_found_fn is not None:
                self.not_found_fn(locals())
                return None
            else:
                raise exceptions.RequiredSecretNotFoundException

        return secret

    def write(
        self,
        value: any,
        env: str = None,
        secretsmanager: str = None,
    ) -> None:
        if value is None:
            raise exceptions.SecretValueNoneException

        if env is not None:
            if os.environ.get(env) != value:
                os.environ[env] = value

                entry = self.cache_env.get(env)
                if entry is not None:
                    self.cache_env.set(
                        cache.CacheEntry(
                            env,
                            value,
                            change_callback_fn=entry.change_callback_fn,
                        ),
                    )
                    if entry.change_callback_fn is not None:
                        entry.change_callback_fn(locals())

        if secretsmanager is not None:
            try:
                secret = self.get_secretsmanager_secret(secretsmanager)
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    secret = None
                else:
                    raise e

            if secret != value:
                self.update_secretsmanager_secret(secretsmanager, value)

                entry = self.cache_secretsmanager.get(env)
                if entry is not None:
                    self.cache_secretsmanager.set(
                        cache.CacheEntry(
                            env,
                            value,
                            change_callback_fn=entry.change_callback_fn,
                        ),
                    )
                    if entry.change_callback_fn is not None:
                        entry.change_callback_fn(locals())

    def string(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: str = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[str]:
        return self.get(
            env=env,
            secretsmanager=secretsmanager,
            required=required,
            default=default,
            change_callback_fn=change_callback_fn,
        )

    def integer(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: int = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[int]:
        val = self.get(
            env=env,
            secretsmanager=secretsmanager,
            required=required,
            default=default,
            change_callback_fn=change_callback_fn,
        )
        return int(val) if val is not None else None

    def float(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: float = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[float]:
        val = self.get(
            env=env,
            secretsmanager=secretsmanager,
            required=required,
            default=default,
            change_callback_fn=change_callback_fn,
        )
        return float(val) if val is not None else None

    def boolean(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: bool = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[bool]:
        val = self.get(
            env=env,
            secretsmanager=secretsmanager,
            required=required,
            default=default,
            change_callback_fn=change_callback_fn,
        )
        return (
            (val if type(val) == bool else val.lower() == "true")
            if val is not None
            else None
        )
