import os, boto3
from typing import Optional, Callable, Dict

from . import exceptions


class Config:
    def __init__(
        self,
        aws_prefix: str = "",
        namespace: str = None,
        not_found_fn: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        aws_access_key_id = os.environ.get(f"{aws_prefix}AWS_ACCESS_KEY_ID")
        if aws_access_key_id is None:
            raise exceptions.AWSMissingAccessKeyIdException

        aws_secret_access_key = os.environ.get(f"{aws_prefix}AWS_SECRET_ACCESS_KEY")
        if aws_secret_access_key is None:
            raise exceptions.AWSMissingSecretAccessKeyException

        aws_session_token = os.environ.get(f"{aws_prefix}AWS_SESSION_TOKEN")
        if aws_session_token is None:
            raise exceptions.AWSMissingSessionTokenException

        region_name = os.environ.get(f"{aws_prefix}AWS_REGION")
        if region_name is None:
            raise exceptions.AWSMissingRegionException

        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name,
        )

        self.session = session
        self.namespace = namespace
        self.not_found_fn = not_found_fn
        self.secretsmanager = self.session.client("secretsmanager")

    # Secrets Manager
    def get_key(self, secret_id) -> str:
        if self.namespace is not None:
            secret_id = f"{self.namespace}/{secret_id}"
        return secret_id

    def get_secret(self, secret_id: str) -> str:
        response = self.secretsmanager.get_secret_value(
            SecretId=self.get_key(secret_id)
        )
        return response.get("SecretString")

    def get(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: any = None,
    ) -> str:
        secret = os.environ.get(env)

        if secret is None and secretsmanager is not None:
            try:
                secret = self.get_secret(secretsmanager)
            except self.secretsmanager.exceptions.ResourceNotFoundException:
                secret = None
            except Exception as err:
                raise err

        if secret is None and default is not None:
            secret = default

        if secret is None and required:
            if self.not_found_fn is not None:
                self.not_found_fn(locals())
            raise exceptions.RequiredSecretNotFoundException

        return secret

    def string(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: str = None,
    ) -> str:
        return self.get(
            env=env, secretsmanager=secretsmanager, required=required, default=default
        )

    def integer(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: int = None,
    ) -> int:
        return int(
            self.get(env=env, secretsmanager=secretsmanager, required=required, default=default),
        )

    def float(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: float = None,
    ) -> float:
        return float(
            self.get(env=env, secretsmanager=secretsmanager, required=required, default=default)
        )

    def boolean(
        self,
        env: str = None,
        secretsmanager: str = None,
        required: bool = None,
        default: bool = None,
    ) -> bool:
        return bool(
            self.get(env=env, secretsmanager=secretsmanager, required=required, default=default).lower() == "true"
        )
