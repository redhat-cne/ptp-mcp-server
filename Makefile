CONTAINER_TOOL ?= podman
IMAGE_REPO ?= quay.io/redhat-cne
IMAGE_TAG ?= latest

SERVER_IMAGE ?= $(IMAGE_REPO)/ptp-mcp-server:$(IMAGE_TAG)
BYOK_IMAGE ?= $(IMAGE_REPO)/ptp-ols-byok:$(IMAGE_TAG)

RAG_TOOL_IMAGE ?= registry.redhat.io/openshift-lightspeed-tech-preview/lightspeed-rag-tool-rhel9:latest
BYOK_OUTPUT_DIR ?= /tmp/byok-output
DOCS_DIR ?= docs

.PHONY: docker-build docker-push byok-build byok-push deploy test

docker-build:
	$(CONTAINER_TOOL) build -t $(SERVER_IMAGE) .

docker-push:
	$(CONTAINER_TOOL) push $(SERVER_IMAGE)

byok-build:
	mkdir -p $(BYOK_OUTPUT_DIR)
	$(CONTAINER_TOOL) run --rm --device=/dev/fuse \
		-v $(XDG_RUNTIME_DIR)/containers/auth.json:/run/user/0/containers/auth.json:Z \
		-v ./$(DOCS_DIR):/markdown:Z \
		-v $(BYOK_OUTPUT_DIR):/output:Z \
		$(RAG_TOOL_IMAGE)
	$(CONTAINER_TOOL) load < $(BYOK_OUTPUT_DIR)/byok-image.tar
	$(CONTAINER_TOOL) tag localhost/byok-image:latest $(BYOK_IMAGE)

byok-push:
	$(CONTAINER_TOOL) push $(BYOK_IMAGE)

deploy:
	cd k8s && kustomize edit set image quay.io/redhat-cne/ptp-mcp-server=$(SERVER_IMAGE) && cd ..
	oc apply -k k8s/

test:
	python quick_test.py
