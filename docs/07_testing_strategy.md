
---

## Document 7: `7_testing_strategy.md`

```markdown
# DOCUMENT 7: TESTING, VALIDATION & ACCEPTANCE CRITERIA

## 1. Unit Tests (per file – examples)

- `test_raycaster.py`: feed known pixel + telemetry → assert output coordinate within 0.1m of pre‑computed value.
- `test_nms.py`: synthetic boxes, ensure correct suppression.
- `test_json_serializer.py`: compare output JSON against schema and example.

Run: `pytest tests/unit/`

## 2. Integration Tests

- **Full pipeline on recorded flight** (`tests/integration/test_replay.py`): Feed a 30‑second log of frames + telemetry, compare output targeting packets to ground truth (manually labelled). Pass if mAP > 85% on that replay.
- **Telemetry sync test**: artificially shift timestamps, ensure sync falls back to nearest neighbour.

Run: `pytest tests/integration/`

## 3. Hardware‑in‑the‑Loop (HITL)

- Use AirSim + ROS2 to simulate a UAS. The AI module runs on the actual Jetson.  
  **Acceptance:** For 10 simulated target runs (different positions), CEP < 5m, latency < 100ms.

## 4. Adversarial Test Suite (script `tests/adversarial/run.sh`)

| Test                | Condition                                      | Pass Criterion                                   |
|---------------------|------------------------------------------------|--------------------------------------------------|
| Occlusion           | Cover 30% of target with simulated leaf texture | Confidence > 0.4                                 |
| Camouflage          | Random camouflage pattern on target (synthetic) | Recall drop < 10% relative to baseline          |
| Low light           | Brightness reduced to 10% of normal            | Recall drop < 15%                                |
| GPS denial          | Inject GPS outage for 10 seconds               | Fallback to visual odometry; still outputs bearing |

## 5. Acceptance Criteria (Go/No‑Go for field trial)

- [ ] mAP@50 ≥ 80% on held‑out test set.
- [ ] 95th percentile latency on Jetson ≤ 110 ms.
- [ ] Geolocation CEP ≤ 5m (averaged over 100 targets at 100m AGL).
- [ ] No segmentation fault or memory leak over 2‑hour continuous run.
- [ ] Unit test pass rate = 100%.
- [ ] Integration test (replay) passes with mAP > 85%.