CONTAINER_TOOL ?= podman
IMAGE_REPO ?= quay.io/redhat-cne
IMAGE_TAG ?= latest

SERVER_IMAGE ?= $(IMAGE_REPO)/ptp-mcp-server:$(IMAGE_TAG)

.PHONY: docker-build docker-push deploy test test-server unit-test lint

docker-build:
	$(CONTAINER_TOOL) build -t $(SERVER_IMAGE) .

docker-push:
	$(CONTAINER_TOOL) push $(SERVER_IMAGE)

deploy:
	cd k8s && kustomize edit set image quay.io/redhat-cne/ptp-mcp-server=$(SERVER_IMAGE) && cd ..
	oc apply -k k8s/

test:
	python quick_test.py

test-server:
	python3 test_ptp_server.py

# Cluster-free unit tests (no live cluster required)
unit-test:
	pytest tests/ -v

# Lint the cluster-free unit-test harness. Scoped to tests/ because the legacy
# modules predate any lint config and carry many pre-existing style violations;
# linting them is tracked as follow-up work, not part of this change.
lint:
	flake8 tests/
