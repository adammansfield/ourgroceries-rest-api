include scripts/make/build_image.mk
include scripts/make/crossplatform.mk
include scripts/make/run_tests.mk
include scripts/make/silent.mk

app := $(shell $(BASENAME) $(CURDIR))
port ?= 1200

bin_dir := _bin
# TODO: Remove gen_dir when openapi-generator is removed
gen_dir := _gen
test_dir := _test

# TODO: Remove non_gen_src when openapi-generator is removed
non_gen_src:=$(shell find internal -name "*.go" ! -name logger.go ! -name main.go ! -name model_*.go ! -name routers.go)

output := $(bin_dir)/openapi
# TODO: combine internal_src and pkg_src to src when openapi-generator is removed
internal_src := $(shell $(FIND) internal *.go version.go)
pkg_src := $(shell $(FIND) pkg *.go)
test_large_success := $(test_dir)/test_large_success
test_small_success := $(test_dir)/test_small_success
version_file := internal/go/version.go

.PHONY: build
build: $(gen_dir) $(output) ## Build the container

.PHONY: build-nc
build-nc: $(gen_dir) $(bin_dir) $(version_file) ## Build the container without caching
	$(call build_image,$(app),$(output),--no-cache)

.PHONY: clean
clean: ## Clean the project
	$(CLEAN)

.PHONY: help
help:
	$(HELP)
.DEFAULT_GOAL := help

# TODO: replace golint with just 'golint ./...' when openapi-generator is removed
# TODO: replace go vet with just 'go vet ./...' when openapi-generator is removed
.PHONY: lint
lint: ## Run gofmt, golint, and go vet
	@echo 'gofmt -s -w ./...'
	gofmt -s -l .
	gofmt -s -w .
	@echo 'golint $(non_gen_src)'
	golint $(non_gen_src)
	@echo 'golint ./pkg/...'
	golint ./pkg/...
	@echo 'go vet ./internal/go/...'
	go vet ./internal/go/...
	@echo 'go vet ./pkg/...'
	go vet ./pkg/...

.PHONY: push
push: ## Push the container to Docker Hub
	./scripts/make/push.sh $(app)

.PHONY: run
run: ## Run the container
	docker run -i -t --rm -p=$(port):8080 --name="$(app)" $(app)

.PHONY: stop
stop: ## Stop and remove the running container
	docker stop $(app)
	docker rm $(app)

.PHONY: test
test: $(test_small_success) ## Run the small (unit) tests

.PHONY: test-large
test-large: $(test_large_success) ## Run the large (end-to-end) tests

$(bin_dir):
	mkdir $@

$(gen_dir): api/openapi.yaml
	docker build -t $(app)-generate -f build/package/Dockerfile.generate .
	$(EXTRACT) $(app)-generate /gen $(gen_dir)
	$(CP) $(gen_dir)$(SEP)servers$(SEP)go/go internal/go
	$(CP) $(gen_dir)$(SEP)servers$(SEP)go/main.go internal/main.go
	$(RM) internal$(SEP)go$(SEP)api_default.go

$(output): $(bin_dir) $(internal_src) $(pkg_src) $(version_file)
	$(call build_image,$(app),$(output))

$(test_large_success): $(gen_dir) $(internal_src) $(pkg_src) $(test_dir) $(version_file)
	$(call run_tests,large_test)
	$(TOUCH) $@

$(test_small_success): $(gen_dir) $(internal_src) $(pkg_src) $(test_dir) $(version_file)
	$(call run_tests,small_test)
	$(TOUCH) $@

$(test_dir):
	mkdir $@

$(version_file): $(gen_dir) $(internal_src) $(pkg_src)
	$(VERSION)
