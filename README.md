# gconfig

gconfig is the shared library used by Gordian to configure applications.
It supports environment variables, NexusConfigService, AWS Secret Manager,
defaults etc.

Read order: `env` → `nexus` → `secretsmanager` → `default`. Each source is
only consulted if the previous one produced nothing; nexus errors fall
through silently to the next source.

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

## NexusConfigService source

gconfig does not depend on the nexus client; services that want the `nexus=`
source construct a `ConfigsClient` themselves (see `nexus-client-py`) and
inject it once at startup. Without an injected client, `nexus=` is ignored
and reads behave exactly as before.

```
from gconfig import Config
from nexus_client_py.configs import ConfigsClient

config = Config(
    secretsmanager_prefix="corev2",
    nexus_client=build_nexus_client(),  # service-owned ConfigsClient setup
)

# env wins if set; otherwise nexus; falls back to Secrets Manager, then default
redis_url = config.string(
    env="REDIS_URL",
    nexus="REDIS_URL",
    secretsmanager="REDIS_URL",
    required=True,
)
```

Notes:

- Nexus failures (and redacted values returned without `read_sensitive`
  permission) fall through silently to the next source — Secrets Manager
  while the call site still passes `secretsmanager=`, otherwise `default=`.
- `GCONFIG_NEXUS_DISABLED_KEYS` is the per-key kill switch: a comma-separated
  key list read once at `Config()` construction. Any listed key behaves as if
  `nexus=` weren't passed. Set it via `heroku config:set` (or the task
  definition env on ECS) and restart to force keys back to Secrets Manager
  without a deploy.
