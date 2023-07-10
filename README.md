# gconfig

gconfig is the shared library used by Gordian to configure applications.
It supports environment variables, AWS Secret Manager, defaults etc.

```
from gconfig import Config


if __name__ == "__main__":
    def notfound(locals: dict):
        print(f"Environment variable {locals.get('env')} not found")

    config = Config(
        namespace="test",
        not_found_fn=notfound,
    )

    redis_url = config.string(env="REDIS_URL", secretsmanager="REDIS_URL", required=True)
    print(redis_url, type(redis_url))

    redis_port = config.integer(env="REDIS_PORT", secretsmanager="REDIS_PORT", default=6379)
    print(redis_port, type(redis_port))

    redis_enabled = config.boolean(env="REDIS_ENABLED", secretsmanager="REDIS_ENABLED", default=True)
    print(redis_enabled, type(redis_enabled))

```
