# DOCUMENT 4: AI/ML PIPELINE – DATA VERSIONING & ACTIVE LEARNING

## 1. DVC Workflow (Step‑by‑Step)

1. **Pull data:** `dvc pull` – downloads latest dataset from S3/GS bucket.
2. **Add new labelled images:** place in `data/processed/v1.2/images/`, update `.txt` labels.
3. **Register changes:** `dvc add data/processed` → `git commit` + `dvc push`.
4. **Training script** always reads from `data/processed/current` which is a symlink to the latest versioned folder.

## 2. Active Learning Loop (Human‑in‑the‑loop)

- After each deployment, log all low‑confidence detections (confidence between 0.3 and 0.6) to `logs/low_confidence/`.
- Weekly, a script `scripts/prepare_active_learning.py` copies those images + predictions to a new Label Studio project.
- Annotator corrects the bounding boxes / classes.
- Exported annotations become a new dataset version (v1.3) → retrain.

## 3. Augmentation Pipeline Specification (Albumentations)

Applied on‑the‑fly during training (deterministic, seed fixed):

| Augmentation              | Probability | Parameters                                           |
|---------------------------|-------------|------------------------------------------------------|
| RandomResizedCrop         | 0.8         | scale=(0.6,1.0)                                      |
| HorizontalFlip            | 0.5         | –                                                    |
| VerticalFlip              | 0.3         | –                                                    |
| Rotate                    | 0.7         | limit=15°, border_mode=reflect                       |
| HueSaturationValue        | 0.6         | hue=10, sat=30, val=20                               |
| GaussNoise                | 0.4         | var_limit=(10,50)                                    |
| CoarseDropout (occlusion) | 0.3         | max_holes=8, max_height=0.1, max_width=0.1           |
| ToFloat                   | 1.0         | –                                                    |

**Synthetic weather** (offline, applied to synthetic data only): fog, rain, glare, low‑light.

## 4. Dataset Version Naming Convention

- `vX.Y` where X = major (class set changes), Y = minor (new annotations, bug fixes).
- Example: `v1.0` = initial 7 classes, 10k instances. `v1.1` = same classes, 12k instances.
- Always keep a `CHANGELOG.md` inside the versioned folder.

## 5. Data Quality Gates

Before accepting a new dataset version, run `scripts/dataset_stats.py` and verify:
- No class has < 500 instances.
- Minimum box size > 5×5 pixels after scaling to 640×640.
- No duplicate images (by perceptual hash).
- Train/val/test split has no class leakage (stratified).