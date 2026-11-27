# Makefile — AI Business Detective
# Usage: make <target>

.PHONY: help install dev test lint typecheck build clean

help:
	@echo ""
	@echo "AI Business Detective — available targets:"
	@echo "  install     Install Python + Node dependencies"
	@echo "  dev         Start FastAPI backend in reload mode"
	@echo "  test        Run all 50 pytest tests"
	@echo "  lint        Run ESLint on web/"
	@echo "  typecheck   Run TypeScript type-check on web/"
	@echo "  build       Build Next.js static export"
	@echo "  clean       Remove build artefacts"
	@echo ""

install:
	pip install -r requirements.txt
	cd web && npm install

dev:
	uvicorn app:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest -v

lint:
	cd web && npm run lint

typecheck:
	cd web && npm run typecheck

build:
	cd web && NEXT_OUTPUT_EXPORT=true npm run build

clean:
	rm -rf web/.next web/out __pycache__ .pytest_cache
	find . -name "*.pyc" -delete
