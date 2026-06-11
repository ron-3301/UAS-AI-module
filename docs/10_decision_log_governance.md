# DOCUMENT 10: DECISION LOG GOVERNANCE (How to Use DECISIONS.md)

## 1. Purpose

The `DECISIONS.md` file is the single source of truth for **why** the project is built the way it is. Every future AI model or developer joining the project must read it before writing code.

## 2. When to Log a Decision

Log a decision when:
- You choose one technology/library over another (e.g., YOLOv8m vs RT-DETR).
- You set a threshold or hyperparameter that is not obvious (e.g., confidence=0.45).
- You change an API or JSON schema field.
- You resolve a trade‑off (e.g., accuracy vs latency).
- You encounter a bug that required a non‑trivial fix.

## 3. Format (copy exactly)

```markdown
## DEC-XXX | YYYY-MM-DD | Phase X | Category | Short title

**Decision:**  
[One sentence stating the choice]

**Alternatives considered:**  
[What else was evaluated]

**Rationale:**  
[Why this choice, including data/benchmarks if available]

**Impact:**  
[What files/configs/tests are affected]

**Status:** ACTIVE | SUPERSEDED BY DEC-YYY | REVERTED
Categories: Architecture | Data | Training | Deployment | API | Testing | Tooling

4. Example Entry
markdown
## DEC-001 | 2025-06-01 | Phase 3 | Architecture | YOLOv8m over RT-DETR

**Decision:** Use Ultralytics YOLOv8m as the primary detection model.

**Alternatives considered:** RT-DETR-L, YOLOv10m.

**Rationale:** On Jetson Orin, YOLOv8m achieved 83% mAP at 92ms latency; RT-DETR-L gave 85% mAP but 134ms latency – outside the 100ms budget.

**Impact:** All training scripts and the TensorRT export pipeline are written for Ultralytics API. Switching models would require rewriting `src/detection/yolo_wrapper.py`.

**Status:** ACTIVE
5. Workflow
Before starting a new development session, review the last 5 decisions.

When a decision is superseded, change its status and write a new decision explaining why the old one no longer holds.

Never delete or edit old decisions – only add new ones or mark as superseded.