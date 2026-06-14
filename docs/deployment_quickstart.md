# Deployment Quickstart

This is deployment scaffolding for the rebuilt advisory runtime. It is not a full
Jetson bring-up guide yet.

## Install layout

Recommended runtime paths:

```text
/opt/uas-ai-module/              project checkout/package
/etc/uas-ai-module/inference.json runtime config
/etc/uas-ai-module/uas-ai-module.env environment file
/var/log/uas-ai-module/          logs
/var/lib/uas-ai-module/          local state
```

## Preflight checks

From the project root:

```bash
python scripts/check_runtime_deps.py
python scripts/validate_assets.py
PYTHONPATH=src python -m uas_ai_module.cli --dry-run --validate-output-schema
python scripts/jetson_health_check.py
```

## systemd

Copy:

```bash
sudo cp deploy/systemd/uas-ai-module.service /etc/systemd/system/uas-ai-module.service
sudo cp deploy/systemd/uas-ai-module.env.example /etc/uas-ai-module/uas-ai-module.env
sudo systemctl daemon-reload
sudo systemctl enable uas-ai-module
```

The current service uses dry-run mode until real runtime backends are wired. Do
not deploy it as an operational camera pipeline until model/backend integration is
complete and tested.

## Log rotation

Copy:

```bash
sudo cp deploy/logrotate/uas-ai-module /etc/logrotate.d/uas-ai-module
```
