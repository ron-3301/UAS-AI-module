# DOCUMENT 12: SAFETY, ETHICS & RULES-OF-ENGAGEMENT POSTURE

> Doc 1 §3 stated in one bullet that the module outputs *targeting recommendations only* and downstream weapons have their own interlocks. For a system whose name contains the word **Targeting**, that single sentence is insufficient. This document makes the safety posture auditable.

## 1. Operating Principle: Human-on-the-Loop, Never Human-out-of-the-Loop

The AI module is **advisory**. It MUST NOT:
- Issue commands to any weapon, weapon-bay, or release mechanism.
- Modify autopilot waypoints or flight-control surfaces.
- Suppress, fuse, or alter the targeting packet of another sensor.

The AI module MUST:
- Emit one outgoing UDP datagram per frame containing **recommendations**, each labelled with confidences and a `validity_flag`.
- Tag every recommendation with the model versions (`detector_sha`, `classifier_sha`) and dataset version (`dataset_version`) that produced it, so any downstream decision is traceable to a reproducible artefact.

## 2. Hard Refusals (output-side filters)

The output layer (`src/output/json_serializer.py`) MUST suppress a detection from the targeting packet when **any** of the following is true (these filters are non-bypassable in code; they are not config-tunable below the listed floors):

| Filter                                  | Threshold                                              |
|-----------------------------------------|--------------------------------------------------------|
| Detection confidence                    | `< 0.30`                                               |
| Identification confidence (if required) | sub-label = `Civilian*` AND id_conf > 0.50 ⇒ drop      |
| Geolocation CEP                         | `> 25 m` ⇒ keep detection, set `validity_flag=false`   |
| GPS denied + no visual-odometry lock    | set `validity_flag=false`, do not emit `geolocation{}` |
| Class = `Person` AND altitude_agl < 30 m | drop (proximity-to-bystander safeguard)               |

Suppressed detections are still written to the SQLite mission log with a `suppression_reason` field for after-action review.

## 3. Civilian / Non-combatant Protection

- The identification classifier explicitly distinguishes `Civilian`, `Civilian-Sedan`, `Civilian-Truck`, `Combatant-Unarmed`.
- Their `class_weights.yaml` override is ≤ 0.15 (see Doc 11).
- A confirmed `Civilian` sub-label with id_conf > 0.5 is **dropped** from the targeting packet (see §2).
- This behaviour is verified by a dedicated test: `tests/adversarial/test_civilian_suppression.py` is part of the Go/No-Go suite (Doc 7 §5) and a failure is a **hard block** on field trial.

## 4. Auditability

Every targeting packet carries:
```json
"audit": {
  "detector_sha":    "yolov8m_uas_v1@a3f9c2",
  "classifier_sha":  "effnetb3_id_v1@7b1d4e",
  "dataset_version": "v1.2",
  "config_sha":      "inference.yaml@e0c81a",
  "ruleset_version": "ROE-2026.1"
}
```
The SQLite mission log retains the full packet (not just a summary) for ≥ 30 days or per operator policy.

## 5. Fail-Safe Defaults

- On any uncaught exception in the pipeline: emit `{"detections": [], "error": {...}, "validity_flag": false}` rather than the last known good packet.
- On thermal throttling: degrade resolution before dropping safety filters; never lower the §2 thresholds.
- On model load failure for the classifier: continue with detector-only output, but force `identification = null` (don’t fabricate sub-labels).

## 6. Out-of-Scope (explicit)

This module does NOT implement:
- Rules of Engagement logic specific to a theatre of operations — that belongs to the ground-station/C2 system.
- Friend-or-Foe (IFF) interrogation.
- Collateral-damage estimation.

These are the integrator’s responsibility and should consume our packet, not extend it in-process.
