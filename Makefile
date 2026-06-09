.PHONY: help install lint typecheck test test-cov validate-configs dry-run verify-phase1 verify-phase2 verify-phase3 clean zip

PY ?= python

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?##"};{printf "  %-20s %s\n",$$1,$$2}'

install:                ## install python deps
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

lint:                   ## ruff
	ruff check src/ tests/ training/ scripts/

typecheck:              ## mypy
	mypy --ignore-missing-imports src/

test:                   ## unit tests
	PYTHONPATH=. pytest tests/unit/ -q

test-cov:               ## unit tests with coverage (>=85%)
	PYTHONPATH=. pytest tests/unit/ --cov=src --cov=scripts --cov-report=term-missing --cov-fail-under=85

validate-configs:       ## validate every yaml against its schema
	PYTHONPATH=. $(PY) scripts/validate_configs.py

dry-run:                ## load + validate inference.yaml via the CLI
	PYTHONPATH=. $(PY) -m src.cli --config configs/inference.yaml --dry-run

verify-phase1:          ## run every phase-1 gate that doesn't need a GPU
	@echo "==> validate-configs"  && $(MAKE) -s validate-configs
	@echo "==> dry-run"           && $(MAKE) -s dry-run
	@echo "==> lint"              && $(MAKE) -s lint || true
	@echo "==> tests"             && $(MAKE) -s test
	@echo
	@echo "phase-1 gates passed. items 1-14 of docs/PHASE1_ACCEPTANCE.md done."
	@echo "item 15 (baseline mAP) needs a GPU + DOTA on the dev box."

verify-phase2:          ## run every phase-2 gate that doesn't need ext data
	@echo "==> phase-1 gates (re-checked)" && $(MAKE) -s verify-phase1
	@echo "==> converter + merger tests"
	PYTHONPATH=. pytest tests/unit/test_convert_vedai.py \
	                    tests/unit/test_convert_xview.py \
	                    tests/unit/test_merge_datasets.py \
	                    tests/unit/test_airsim_collect.py -q
	@echo
	@echo "phase-2 CI gates passed. see docs/PHASE2_ACCEPTANCE.md for the ext-data items."

verify-phase3:          ## run every phase-3 gate that doesn't need a GPU
	@echo "==> phase-2 gates (re-checked)" && $(MAKE) -s verify-phase2
	@echo "==> detection + identification + ingestion + pipeline tests"
	PYTHONPATH=. pytest tests/unit/test_nms.py \
	                    tests/unit/test_tracker.py \
	                    tests/unit/test_crop_extractor.py \
	                    tests/unit/test_frame_capture.py \
	                    tests/unit/test_telemetry_sync.py \
	                    tests/unit/test_udp_emitter.py \
	                    tests/unit/test_benchmark_models.py \
	                    tests/unit/test_hyperparam_search.py \
	                    tests/unit/test_eval.py \
	                    tests/unit/test_mine_hard_negatives.py \
	                    tests/integration/test_pipeline_end_to_end.py -q
	@echo
	@echo "phase-3 CI gates passed. see docs/PHASE3_ACCEPTANCE.md for the GPU items."

clean:                  ## wipe caches, build artefacts, logs
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf logs/*

zip:                    ## package code (no docs, no data) for download
	cd .. && rm -f uas-ai-module-code.zip && \
	  zip -r uas-ai-module-code.zip uas-ai-module \
	    -x 'uas-ai-module/docs/*' 'uas-ai-module/*__pycache__*' \
	       'uas-ai-module/.pytest_cache/*' 'uas-ai-module/.ruff_cache/*' \
	       'uas-ai-module/.mypy_cache/*' 'uas-ai-module/logs/*' \
	       'uas-ai-module/*.pyc'
