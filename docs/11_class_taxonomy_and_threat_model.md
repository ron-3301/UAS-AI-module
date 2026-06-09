# DOCUMENT 11: CLASS TAXONOMY & THREAT SCORING MODEL

> Fills gaps in Docs 2 (Layer 3 threat_scorer) and Doc 6 (`class_weights.yaml` referenced but never defined).

## 1. Detection Class Taxonomy (v1.0 — 7 classes)

The detector (`yolov8m_uas_v1`) is trained on the following **flat, mutually exclusive** classes. Sub-types are resolved by the identification classifier (Layer 3), not the detector.

| id | class_name         | Description                                                          | Typical pixel size @ 100 m AGL |
|----|--------------------|----------------------------------------------------------------------|--------------------------------|
| 0  | Person             | Standing or walking human, with or without backpack                  | 8–25 px                        |
| 1  | Vehicle-Wheeled    | Cars, SUVs, trucks, technicals, Humvees                              | 30–120 px                      |
| 2  | Vehicle-Tracked    | Tanks, APCs, IFVs, bulldozers                                        | 40–140 px                      |
| 3  | Aircraft-Rotary    | Helicopters (on ground or low hover)                                 | 60–200 px                      |
| 4  | Aircraft-Fixed     | Fixed-wing aircraft on ground or runway                              | 80–300 px                      |
| 5  | Watercraft         | Boats, RHIBs, small ships                                            | 30–250 px                      |
| 6  | Structure-Temp     | Tents, makeshift shelters, sandbag positions                         | 30–150 px                      |

**Background** is implicit (no class id). All other objects (trees, rocks, civilians’ homes that are clearly permanent buildings, livestock) are treated as background and must not produce detections.

### 1.1 Identification sub-classes (Layer 3, EfficientNet-B3)
Each detection class has 4–12 fine-grained sub-labels. Examples:
- `Vehicle-Wheeled` → {Humvee, Toyota-Hilux, Ural-4320, BTR-wheeled, Civilian-Sedan, Civilian-Truck, Unknown}
- `Vehicle-Tracked` → {T-72, T-90, BMP-2, M1-Abrams, Bulldozer, Unknown}
- `Person`          → {Combatant-Armed, Combatant-Unarmed, Civilian, Unknown}

The complete sub-label list lives in `configs/identification_labels.yaml` (versioned with the classifier weights).

## 2. Threat Scoring Formula

```
threat_score = clip( w_class · f_det · f_id · f_prox · f_motion · f_context , 0.0, 1.0 )
```

| Factor       | Range      | Source                                                                    |
|--------------|------------|---------------------------------------------------------------------------|
| `w_class`    | 0.0 – 1.0  | `configs/class_weights.yaml` (per detection class)                        |
| `f_det`      | 0.1 – 1.0  | Detector confidence, clipped at 0.1 to avoid zero-multiply blackholes     |
| `f_id`       | 0.5 – 1.0  | `0.5 + 0.5 · id_confidence` (so an unknown sub-class still contributes)   |
| `f_prox`     | 0.3 – 1.0  | `1.0 − clip(slant_range_m / 500.0, 0, 0.7)` — closer ⇒ higher             |
| `f_motion`   | 0.7 – 1.2  | `1.0` default; +0.2 if tracker reports speed > 5 m/s; −0.3 if static > 30 s |
| `f_context`  | 0.5 – 1.5  | Mission-profile multiplier from `configs/mission_profile.yaml` (e.g. urban=0.5, contested=1.5) |

`slant_range_m` is computed by the geolocation engine (Layer 4) from camera position and ray-cast intersection.

### 2.1 Worked example
A Humvee detected at 120 m slant range, det_conf=0.91, id_conf=0.84, moving at 7 m/s, default context:

```
w_class      = 0.80   (Vehicle-Wheeled, see class_weights.yaml)
f_det        = 0.91
f_id         = 0.5 + 0.5·0.84 = 0.92
f_prox       = 1.0 − clip(120/500, 0, 0.7) = 1.0 − 0.24 = 0.76
f_motion     = 1.20
f_context    = 1.00
threat_score = 0.80·0.91·0.92·0.76·1.20·1.00 = 0.611 → 0.61
```

## 3. `configs/class_weights.yaml` (canonical values)

```yaml
version: "1.0"
# Detection-class threat weights (w_class). Range [0,1].
# Higher = more operationally significant. Reviewed each mission cycle.
weights:
  Person:           0.50
  Vehicle-Wheeled:  0.80
  Vehicle-Tracked:  0.95
  Aircraft-Rotary:  0.90
  Aircraft-Fixed:   0.85
  Watercraft:       0.60
  Structure-Temp:   0.40
# Optional per-sub-label overrides (look-up by identification label).
overrides:
  Civilian:         0.05
  Civilian-Sedan:   0.10
  Civilian-Truck:   0.15
  T-90:             1.00
  M1-Abrams:        1.00
  Combatant-Armed:  0.95
```

## 4. Add / remove a class — checklist
1. Bump dataset version major (vX.Y → v(X+1).0) per Doc 4 §4.
2. Update `configs/class_weights.yaml` (`version` bump).
3. Retrain detector AND classifier — do **not** ship one without the other.
4. Add an entry to `DECISIONS.md` (Category: Data).
5. Update `docs/11_class_taxonomy_and_threat_model.md` (this file) with new row.
