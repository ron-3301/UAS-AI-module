# How to Provide Unsupported Project Files

If Arena will not accept some project files directly, use one of these approaches.

## Preferred: upload an archive

Try uploading one of:

- `uas-ai-module.zip`
- `uas-ai-module.tar.gz`
- `uas-ai-module.tgz`

Preserve the original directory structure.

Before archiving, exclude heavy/generated files:

```bash
rm -rf .git .venv venv __pycache__ .pytest_cache .mypy_cache .ruff_cache \
       build dist node_modules runs mlruns datasets artifacts .dvc/cache
```

Do not include secrets, API keys, private keys, or production credentials.

## If archives are also unsupported

### 1. Upload a tree listing

Run and paste/upload the output:

```bash
find . -maxdepth 5 -type f | sort
```

If the repo uses git:

```bash
git ls-files | sort
```

### 2. Rename unsupported text files

Some extensions may be blocked even though the content is text. Rename them before upload:

| Original | Rename to |
|---|---|
| `*.py` | `*.py.txt` |
| `*.yaml` / `*.yml` | `*.yaml.txt` |
| `*.proto` | `*.proto.txt` |
| `*.service` | `*.service.txt` |
| `Dockerfile` | `Dockerfile.txt` |
| `*.sh` | `*.sh.txt` |

I can restore the original names after upload.

### 3. Paste critical source files in chunks

Start with these, in order:

1. `src/config.py`
2. `src/pipeline.py`
3. `src/output/json_serializer.py`
4. `src/geolocation/imm_kalman.py`
5. `src/prediction/tcpa.py`
6. `src/detection/yolo_wrapper.py`
7. `src/identification/classifier.py`
8. `src/coordination/track_message.proto`
9. Main scripts under `scripts/`
10. Training scripts under `training/`

### 4. Do not upload large model files unless necessary

For model artifacts (`*.pt`, `*.onnx`, `*.engine`, `*.plan`), provide metadata instead:

```text
filename:
sha256:
size_bytes:
input_shape:
output_shape:
classes:
export_command:
training_dataset_version:
metrics:
```

### 5. For datasets/videos

Do not upload full datasets initially. Provide:

- small representative samples
- dataset manifest
- class counts
- annotation format example
- one image + annotation pair per source type

## Minimum useful bundle

If you can only send a small subset, send:

```text
README.md
pyproject.toml or setup.cfg/setup.py if present
requirements*.txt
src/config.py
src/pipeline.py
src/output/json_serializer.py
schemas/
configs/
tests/
scripts/
training/
```
