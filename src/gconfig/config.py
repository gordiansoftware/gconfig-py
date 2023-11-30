import os
from typing import Callable, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from . import cache, exceptions, parse


class Config:
    def __init__(
        self,
        aws_prefix: str = "",
        aws_session_required: bool = False,
        secretsmanager_prefix: str = None,
        not_found_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        self.aws_prefix = aws_prefix
        self.aws_session_required = aws_session_required
        self.secretsmanager_client = None
        self.secretsmanager_prefix = secretsmanager_prefix
        self.not_found_fn = not_found_fn
        self.cache_env = cache.Cache()
        self.cache_secretsmanager = cache.Cache()

    # Secrets Manager
    def get_secretsmanager(self) -> boto3.client:
        # TODO: add support for checking if the client session is still valid.
        
        if self.secretsmanager_client is None:
            aws_access_key_id = os.environ.get(f"{self.aws_prefix}AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.environ.get(
                f"{self.aws_prefix}AWS_SECRET_ACCESS_KEY"
            )
            region_name = os.environ.get(f"{self.aws_prefix}AWS_REGION")

            # AWS_SESSION_TOKEN is optional, if not provided, assume role will be used.
            aws_session_token = os.environ.get(f"{self.aws_prefix}AWS_SESSION_TOKEN")

            # Assume role IF:
            #   AWS_SESSION_TOKEN is not provided AND
            #   AWS_ACCESS_KEY_ID is provided AND
            #   AWS_SECRET_ACCESS_KEY is provided
            should_assume_role = aws_session_token is None and (
                aws_access_key_id is not None and aws_secret_access_key is not None
            )

            if should_assume_role:
                aws_role_arn = os.environ.get(f"{self.aws_prefix}AWS_ROLE_ARN", None)
                aws_role_session_name = os.environ.get(
                    f"{self.aws_prefix}AWS_ROLE_SESSION_NAME", None
                )

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

            # AWS credentials are expected to be present at this point.
            if self.aws_session_required and aws_access_key_id is None:
                raise exceptions.AWSMissingAccessKeyIdException

            if self.aws_session_required and aws_secret_access_key is None:
                raise exceptions.AWSMissingSecretAccessKeyException

            if self.aws_session_required and aws_session_token is None:
                raise exceptions.AWSMissingSessionTokenException

            if self.aws_session_required and region_name is None:
                raise exceptions.AWSMissingRegionException

            # If the kwargs provided to Session are None
            # we will use the default credentials chain.
            # This will use boto3's default credential chain
            # which includes environment variables, config files, etc.
            # Specifically when running in the AWS environment,
            # the library knows how to pull credentials dynamically.
            # This behavior was manually tested and validated in an ECS container.
            # If this happens, it is up to the user to ensure the role which is
            # used to run the container has the appropriate permissions to access
            # the secrets manager secrets.
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region_name=region_name,
            )

            self.session = session
            self.secretsmanager_client = self.session.client("secretsmanager")

        return self.secretsmanager_client

    def get_secretsmanager_key(self, secret_id, secretsmanager_prefix: str = None) -> str:
        secretsmanager_prefix = secretsmanager_prefix or self.secretsmanager_prefix
        if secretsmanager_prefix is not None:
            secret_id = f"{secretsmanager_prefix}/{secret_id}"
        return secret_id

    def get_secretsmanager_secret(self, secret_id: str, secretsmanager_prefix: str = None) -> str:
        secretsmanager_client = self.get_secretsmanager()
        response = secretsmanager_client.get_secret_value(
            SecretId=self.get_secretsmanager_key(secret_id, secretsmanager_prefix=secretsmanager_prefix)
        )
        return response.get("SecretString")

    def update_secretsmanager_secret(self, secret_id: str, secret: str, secretsmanager_prefix: str = None) -> None:
        secretsmanager_client = self.get_secretsmanager()
        secretsmanager_client.put_secret_value(
            SecretId=self.get_secretsmanager_key(secret_id, secretsmanager_prefix=secretsmanager_prefix),
            SecretString=parse.parse_entry(str, secret),
        )

    def create_secretsmanager_secret(self, secret_id: str, secret: str, secretsmanager_prefix: str = None) -> None:
        secretsmanager_client = self.get_secretsmanager()
        secretsmanager_client.create_secret(
            Name=self.get_secretsmanager_key(secret_id, secretsmanager_prefix=secretsmanager_prefix),
            SecretString=parse.parse_entry(str, secret),
        )

    def get(
        self,
        typ: type,
        env: str = None,
        secretsmanager: str = None,
        default: any = None,
        required: bool = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
        secretsmanager_prefix: str = None,
    ) -> Optional[str]:
        secret = os.environ.get(env) if env is not None else None
        if secret is not None:
            self.cache_env.set(
                cache.CacheEntry(
                    typ,
                    env,
                    secret,
                    change_callback_fn=change_callback_fn,
                ),
            )

        if secret is None and secretsmanager is not None:
            try:
                secret = self.get_secretsmanager_secret(secretsmanager, secretsmanager_prefix=secretsmanager_prefix)
                self.cache_secretsmanager.set(
                    cache.CacheEntry(
                        typ,
                        secretsmanager,
                        secret,
                        change_callback_fn=change_callback_fn,
                    ),
                )
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
        value: str,
        env: str = None,
        secretsmanager: str = None,
        secretsmanager_prefix: str = None,
    ) -> None:
        if value is None:
            raise exceptions.SecretValueNoneException

        if env is not None:
            if os.environ.get(env) != value:
                os.environ[env] = parse.parse_entry(str, value)

                entry = self.cache_env.get(env)
                if entry is not None:
                    self.cache_env.set(
                        cache.CacheEntry(
                            entry.type,
                            env,
                            value,
                            change_callback_fn=entry.change_callback_fn,
                        ),
                    )
                    if entry.change_callback_fn is not None:
                        entry.change_callback_fn(
                            args={**locals(), "value": parse.parse_entry(entry.type, value)}
                        )

        if secretsmanager is not None:
            try:
                secret = self.get_secretsmanager_secret(secretsmanager, secretsmanager_prefix=secretsmanager_prefix)
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    secret = None
                else:
                    raise e

            if secret is None:
                self.create_secretsmanager_secret(secretsmanager, value, secretsmanager_prefix=secretsmanager_prefix)
            elif secret != value:
                self.update_secretsmanager_secret(secretsmanager, value, secretsmanager_prefix=secretsmanager_prefix)

                entry = self.cache_secretsmanager.get(env)
                if entry is not None:
                    self.cache_secretsmanager.set(
                        cache.CacheEntry(
                            entry.type,
                            secretsmanager,
                            value,
                            change_callback_fn=entry.change_callback_fn,
                        ),
                    )
                    if entry.change_callback_fn is not None:
                        entry.change_callback_fn(
                            args={**locals(), "value": parse.parse_entry(entry.type, value)}
                        )

    def string(
        self,
        env: str = None,
        secretsmanager: str = None,
        secretsmanager_prefix: str = None,
        required: bool = None,
        default: str = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[str]:
        return parse.parse_entry(
            str,
            self.get(
                str,
                env=env,
                secretsmanager=secretsmanager,
                secretsmanager_prefix=secretsmanager_prefix,
                required=required,
                default=default,
                change_callback_fn=change_callback_fn,
            ),
        )

    def integer(
        self,
        env: str = None,
        secretsmanager: str = None,
        secretsmanager_prefix: str = None,
        required: bool = None,
        default: int = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[int]:
        return parse.parse_entry(
            int,
            self.get(
                int,
                env=env,
                secretsmanager=secretsmanager,
                secretsmanager_prefix=secretsmanager_prefix,
                required=required,
                default=default,
                change_callback_fn=change_callback_fn,
            ),
        )

    def float(
        self,
        env: str = None,
        secretsmanager: str = None,
        secretsmanager_prefix: str = None,
        required: bool = None,
        default: float = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[float]:
        return parse.parse_entry(
            float,
            self.get(
                float,
                env=env,
                secretsmanager=secretsmanager,
                secretsmanager_prefix=secretsmanager_prefix,
                required=required,
                default=default,
                change_callback_fn=change_callback_fn,
            ),
        )

    def boolean(
        self,
        env: str = None,
        secretsmanager: str = None,
        secretsmanager_prefix: str = None,
        required: bool = None,
        default: bool = None,
        change_callback_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> Optional[bool]:
        return parse.parse_entry(
            bool,
            self.get(
                bool,
                env=env,
                secretsmanager=secretsmanager,
                secretsmanager_prefix=secretsmanager_prefix,
                required=required,
                default=default,
                change_callback_fn=change_callback_fn,
            ),
        )
