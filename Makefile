.PHONY: bootstrap dev lint typecheck test test-backend test-frontend test-rust test-e2e build-web build-sidecar build-desktop build-all

bootstrap:
	./scripts/bootstrap.sh

dev:
	./scripts/dev.sh

lint:
	pnpm lint
	cargo fmt --manifest-path apps/desktop/src-tauri/Cargo.toml --all -- --check
	cargo clippy --manifest-path apps/desktop/src-tauri/Cargo.toml --all-targets --all-features -- -D warnings

typecheck:
	pnpm typecheck

test: test-backend test-frontend test-rust

test-backend:
	uv run pytest -q

test-frontend:
	pnpm test

test-rust:
	cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml

test-e2e:
	pnpm --filter @tracegate/web test:e2e

build-web:
	pnpm --filter @tracegate/web build

build-sidecar:
	./scripts/build-sidecar.sh

build-desktop:
	pnpm --filter @tracegate/desktop build

build-all: build-web build-sidecar build-desktop
