# Classic Models API - Simplified Makefile

.PHONY: build tag push start stop health-check test postman-test clean help version patch minor major

# Default target
.DEFAULT_GOAL := help

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m # No Color

# Plain `docker build`/`docker push` (or podman) — no OpenShift/BuildConfig
# dependency, so this works against any registry on any Kubernetes distribution.
# Tag format matches the CI pipeline (.github/workflows/docker-build.yml):
# vX.Y.Z, derived from the same API_VERSION as scripts/get_version.sh, so a
# manual `make push` produces the exact same tag the CI would produce for
# that version.
# Override REGISTRY/IMAGE_NAME/IMAGE_TAG/CONTAINER_ENGINE as needed, e.g.:
#   make push REGISTRY=quay.io/myorg IMAGE_NAME=classic-models-api IMAGE_TAG=v1.2.3
#   make push CONTAINER_ENGINE=podman
REGISTRY ?= ghcr.io
IMAGE_NAME ?= staillanibm/classic-models-api
IMAGE := $(REGISTRY)/$(IMAGE_NAME)
# Empty by default: derived from the current git tag (v-prefixed) at build
# time, same source of truth as CI. Override explicitly to tag/push something
# other than the current version, e.g. IMAGE_TAG=v1.2.3.
IMAGE_TAG ?=
CONTAINER_ENGINE ?= $(shell command -v docker >/dev/null 2>&1 && echo docker || echo podman)

help: ## Show this help message
	@echo "$(BLUE)Classic Models API - Available Commands$(NC)"
	@echo ""
	@echo "  $(GREEN)build$(NC)        - Build the Docker containers"
	@echo "  $(GREEN)tag$(NC)          - Build and tag the API image as vX.Y.Z (same scheme as CI)"
	@echo "  $(GREEN)push$(NC)         - Build, tag and push the API image to REGISTRY/IMAGE_NAME"
	@echo "  $(GREEN)start$(NC)        - Start the containers (database resets to original data)"
	@echo "  $(GREEN)stop$(NC)         - Stop the containers"
	@echo "  $(GREEN)test$(NC)         - Run the test suite"
	@echo "  $(GREEN)postman-test$(NC) - Run Postman collection tests"
	@echo "  $(GREEN)clean$(NC)       - Clean up test result files"
	@echo "  $(GREEN)health-check$(NC) - Run health check against the API endpoints"
	@echo "  $(GREEN)patch$(NC)        - Bump patch version (0.0.1 -> 0.0.2)"
	@echo "  $(GREEN)minor$(NC)        - Bump minor version (0.0.1 -> 0.1.0)"
	@echo "  $(GREEN)major$(NC)        - Bump major version (0.0.1 -> 1.0.0)"
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make build        # Build containers"
	@echo "  make push REGISTRY=quay.io/myorg IMAGE_NAME=classic-models-api # Build, tag and push"
	@echo "  make push IMAGE_TAG=v1.2.3        # Push a specific tag instead of the derived version"
	@echo "  make push CONTAINER_ENGINE=podman # Use podman instead of docker"
	@echo "  make push TAG_LATEST=1            # Also tag/push :latest"
	@echo "  make start        # Start with fresh database"
	@echo "  make test         # Run all tests"
	@echo "  make postman-test # Run Postman collection tests"
	@echo "  make clean        # Clean up test files"
	@echo "  make health-check # Check if API is working"
	@echo "  make patch         # Bump patch version (0.0.1 -> 0.0.2)"
	@echo "  make minor         # Bump minor version (0.0.1 -> 0.1.0)"
	@echo "  make major         # Bump major version (0.0.1 -> 1.0.0)"

build: ## Build the Docker containers
	@echo "$(BLUE)Building Docker containers...$(NC)"
	@source scripts/get_version.sh && docker-compose build --build-arg API_VERSION=$$API_VERSION
	@echo "$(GREEN)✓ Containers built successfully$(NC)"

# TAG_LATEST=1 also tags/pushes :latest. Off by default: unlike CI (which only
# tags latest when the pushed version is the highest existing semver tag),
# this doesn't check — enable it manually only when you know that's true.
TAG_LATEST ?=

tag: ## Build and tag the API image (REGISTRY/IMAGE_NAME/IMAGE_TAG/CONTAINER_ENGINE/TAG_LATEST)
	@source scripts/get_version.sh && \
		TAG=$${IMAGE_TAG:-v$$API_VERSION} && \
		echo "$(BLUE)Building and tagging $(IMAGE):$$TAG with $(CONTAINER_ENGINE)...$(NC)" && \
		EXTRA_TAGS="" && \
		if [ -n "$(TAG_LATEST)" ]; then EXTRA_TAGS="-t $(IMAGE):latest"; fi && \
		$(CONTAINER_ENGINE) build --build-arg API_VERSION=$$API_VERSION -t $(IMAGE):$$TAG $$EXTRA_TAGS . && \
		echo "$(GREEN)✓ Tagged $(IMAGE):$$TAG$(if $(TAG_LATEST), and $(IMAGE):latest)$(NC)"

push: tag ## Build, tag and push the API image to REGISTRY/IMAGE_NAME
	@source scripts/get_version.sh && \
		TAG=$${IMAGE_TAG:-v$$API_VERSION} && \
		echo "$(BLUE)Pushing $(IMAGE):$$TAG with $(CONTAINER_ENGINE) (make sure you're logged in: $(CONTAINER_ENGINE) login $(REGISTRY))...$(NC)" && \
		$(CONTAINER_ENGINE) push $(IMAGE):$$TAG && \
		if [ -n "$(TAG_LATEST)" ]; then $(CONTAINER_ENGINE) push $(IMAGE):latest; fi
	@echo "$(GREEN)✓ Pushed $(IMAGE)$(NC)"

start: ## Start the containers (database resets to original data)
	@echo "$(BLUE)Starting containers with fresh database...$(NC)"
	@source scripts/get_version.sh && docker-compose down -v && docker-compose up -d
	@echo "$(GREEN)✓ Containers started with fresh database$(NC)"
	@echo "$(YELLOW)API available at: http://localhost:8000/classic-models$(NC)"
	@echo "$(YELLOW)API docs: http://localhost:8000/classic-models/api/docs/$(NC)"

stop: ## Stop the containers
	@echo "$(BLUE)Stopping containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

test: ## Run the test suite
	@echo "$(BLUE)Running test suite...$(NC)"
	@docker-compose up -d
	@docker-compose exec -T api pytest
	@echo "$(GREEN)✓ All tests completed$(NC)"

postman-test: ## Run Postman collection tests
	@echo "$(BLUE)Running Postman collection tests...$(NC)"
	@echo "Note: Make sure the API is running (make start) before running these tests"
	@echo ""
	@if [ -f "Classic_Models_API.postman_collection.json" ]; then \
		newman run Classic_Models_API.postman_collection.json \
			--env-var "base_url=http://localhost:8000/classic-models" \
			--reporters cli,json \
			--reporter-json-export postman-test-results.json \
			--timeout-request 10000 \
			--timeout-script 10000; \
		echo "$(GREEN)✓ Postman tests completed$(NC)"; \
		echo "$(YELLOW)Test results saved to: postman-test-results.json$(NC)"; \
	else \
		echo "$(RED)✗ Postman collection file not found$(NC)"; \
		echo "Expected: Classic_Models_API.postman_collection.json"; \
		exit 1; \
	fi

clean: ## Clean up test result files
	@echo "$(BLUE)Cleaning up test result files...$(NC)"
	@if [ -f "postman-test-results.json" ]; then \
		rm postman-test-results.json; \
		echo "$(GREEN)✓ Removed postman-test-results.json$(NC)"; \
	else \
		echo "$(YELLOW)No test result files to clean$(NC)"; \
	fi

health-check: ## Run health check against the API endpoints
	@echo "$(BLUE)Running health check...$(NC)"
	@echo "Checking API endpoints..."
	@curl -f -s http://localhost:8000/classic-models/api/docs/ > /dev/null && echo "$(GREEN)✓ API documentation is available$(NC)" || echo "$(RED)✗ API documentation is not available$(NC)"
	@curl -f -s http://localhost:8000/classic-models/api/schema/ > /dev/null && echo "$(GREEN)✓ API schema is available$(NC)" || echo "$(RED)✗ API schema is not available$(NC)"
	@curl -f -s -w "%{http_code}" -o /dev/null http://localhost:8000/classic-models/api/auth/signup/ | grep -q "405" && echo "$(GREEN)✓ Authentication endpoints are responding$(NC)" || echo "$(RED)✗ Authentication endpoints are not responding$(NC)"
	@curl -f -s -w "%{http_code}" -o /dev/null http://localhost:8000/classic-models/api/v1/customers/ | grep -q "401\|403" && echo "$(GREEN)✓ Customers endpoint is responding (authentication required)$(NC)" || echo "$(RED)✗ Customers endpoint is not responding$(NC)"
	@curl -f -s -w "%{http_code}" -o /dev/null http://localhost:8000/classic-models/api/v1/products/ | grep -q "401\|403" && echo "$(GREEN)✓ Products endpoint is responding (authentication required)$(NC)" || echo "$(RED)✗ Products endpoint is not responding$(NC)"
	@echo "$(GREEN)✓ Health check completed$(NC)"

patch: ## Bump patch version (0.0.1 -> 0.0.2)
	@echo "$(BLUE)Bumping patch version...$(NC)"
	python scripts/version_manager.py patch
	@echo "$(GREEN)✓ Patch version bumped$(NC)"

minor: ## Bump minor version (0.0.1 -> 0.1.0)
	@echo "$(BLUE)Bumping minor version...$(NC)"
	python scripts/version_manager.py minor
	@echo "$(GREEN)✓ Minor version bumped$(NC)"

major: ## Bump major version (0.0.1 -> 1.0.0)
	@echo "$(BLUE)Bumping major version...$(NC)"
	python scripts/version_manager.py major
	@echo "$(GREEN)✓ Major version bumped$(NC)"