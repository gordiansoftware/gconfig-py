# gconfig

gconfig is the shared library used by Gordian to configure applications.
It supports environment variables, AWS Secret Manager, defaults etc.

```
from gconfig import Config


def not_found_alert(locals: dict):
    print(f"Environment variable {locals.get('env')} not found")

if __name__ == "__main__":
    # export GCONFIG_AWS_REGION=us-west-2
    # export GCONFIG_AWS_ACCESS_KEY_ID=xxx
    # export GCONFIG_AWS_SECRET_ACCESS_KEY=xxx
    # export GCONFIG_AWS_ROLE_ARN=arn:aws:iam::xxx:role/xxx
    # export GCONFIG_AWS_ROLE_SESSION_NAME=xxx-role

    config = Config(
        aws_prefix="GCONFIG_",
        secretsmanager_prefix="corev2",
        not_found_fn=not_found_alert,
    )

    redis_url = config.string(env="REDIS_URL", secretsmanager="REDIS_URL", required=True)
    print(redis_url, type(redis_url))

    redis_port = config.integer(env="REDIS_PORT", secretsmanager="REDIS_PORT", default=6379)
    print(redis_port, type(redis_port))

    redis_enabled = config.boolean(env="REDIS_ENABLED", secretsmanager="REDIS_ENABLED", default=True)
    print(redis_enabled, type(redis_enabled))

```
