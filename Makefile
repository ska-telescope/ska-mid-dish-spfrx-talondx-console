#
# Project makefile for Mid DISH SPFRx Talon-DX Console
#

#
# CAR_OCI_REGISTRY_HOST and PROJECT are combined to define
# the Docker tag for this project. The definition below inherits the standard
# value for CAR_OCI_REGISTRY_HOST = artefact.skao.int and overwrites
# PROJECT to give a final Docker tag of
# artefact.skao.int/ska-tango-examples/powersupply
#
PROJECT = ska-mid-dish-spfrx-talondx-console

ARGS ?=

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-mid-dish-spfrx
DOMAIN ?= cluster.local
SPFRX_ADDRESS ?= 192.168.8.200
SPFRX_TANGO_INSTANCE ?= spfrx
SPFRX_DEFAULT_LOGGING_LEVEL ?= 4
SPFRX_BIN ?= /usr/local/bin
TANGO_PORT ?= 10000
QSFP_CONTROL_PATH ?= /usr/share/bittware/520nmx/cots/utilities/qsfp_control/bin

# RELEASE_NAME is the release that all Kubernetes resources will be labelled
# with
RELEASE_NAME ?= test

OCI_IMAGES ?= ska-mid-dish-spfrx-talondx-console \
	ska-mid-dish-spfrx-talondx-console-deploy \
	ska-mid-dish-spfrx-talondx-console-plot
OCI_IMAGES_TO_PUBLISH ?= $(OCI_IMAGES)
OCI_IMAGE_BUILD_CONTEXT = $(PWD)

# use python3 if not CI job
ifeq ($(strip $(CI_JOB_ID)),)
PYTHON_RUNNER = python3 -m
endif

# Fixed variables
# Timeout for gitlab-runner when run locally
TIMEOUT = 86400

CI_PROJECT_DIR ?= .

XAUTHORITY ?= $(HOME)/.Xauthority
THIS_HOST := $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY ?= $(THIS_HOST):0
JIVE ?= true# Enable jive
WEBJIVE ?= false# Enable Webjive

CI_PROJECT_PATH_SLUG ?= ska-mid-dish-spfrx-talondx-console
CI_ENVIRONMENT_SLUG ?= ska-mid-dish-spfrx-talondx-console
$(shell echo 'global:\n  annotations:\n    app.gitlab.com/app: $(CI_PROJECT_PATH_SLUG)\n    app.gitlab.com/env: $(CI_ENVIRONMENT_SLUG)' > gitlab_values.yaml)

# define private overrides for above variables in here
-include PrivateRules.mak

#
# include makefile to pick up the standard Make targets, e.g., 'make build'
# build, 'make push' docker push procedure, etc. The other Make targets
# ('make interactive', 'make test', etc.) are defined in this file.
#
include .make/release.mk
include .make/make.mk
include .make/python.mk
include .make/oci.mk
include .make/docs.mk
include .release

IMG_DIR := $(PWD)/images/

# Test runner - run to completion job in K8s
# name of the pod running the k8s_tests
TEST_RUNNER = test-runner-$(CI_JOB_ID)-$(RELEASE_NAME)

PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=$(IMG_DIR)

PYTHON_VARS_AFTER_PYTEST = -m "not post_deployment"

PYTHON_SWITCHES_FOR_FLAKE8 = --ignore=E203,E402,E501,F407,W503

PYTHON_LINT_TARGET = $(IMG_DIR)

SPFRX_DATABASE_POD = $(shell kubectl get svc -n $(KUBE_NAMESPACE) | grep databaseds | cut -d ' ' -f1)
SPFRX_TANGO_HOST = $(SPFRX_DATABASE_POD).$(KUBE_NAMESPACE).svc.$(DOMAIN):$(TANGO_PORT)

run:  ## Run docker container
	docker run --rm $(strip $(OCI_IMAGE)):$(release)

# overwrite to use a different JSON
SPFRX_CONFIG_FILE := spfrx-config.json
SPFRX_CONFIG_FILE_PATH = $(IMG_DIR)/spfrx_config/$(SPFRX_CONFIG_FILE)
SPFRX_LOCAL_DIR = $(PWD)/mnt/spfrx-config/
MNT_LOCAL_DIR = $(PWD)/mnt/

# Call the scripts/config-spfrx-tango-host.sh script
#  This will set the TANGO_HOST environment variable on the specified remote host
#  The format should be:
#   TANGO_HOST=databaseds-tango-base.ci-ska-skampi-cbf-automated-pipeline-testing-mid.svc.cluster.local:10000
#  or similar, depending on the k8s configuration
config-spfrx-tango-host: ## Set TANGO_HOST on SPFRx HPS
	@. scripts/config-spfrx-tango-host.sh $(SPFRX_ADDRESS) $(KUBE_NAMESPACE) $(DOMAIN) $(TANGO_PORT)

# Call the scripts/spfrx-deploy-artifacts.sh script
#  This will copy required shell scripts to the specified remote SPFRx HPS host
spfrx-deploy-artifacts: ## Deploy SPFRx artefacts to HPS
	@. scripts/spfrx-deploy-artifacts.sh $(SPFRX_ADDRESS) $(SPFRX_LOCAL_DIR) $(SPFRX_BIN)

# Call the scripts/spfrx-rxpu-ops.sh script to bring UP the RXPU
#  This will perform an ssh command to start the RXPU TANGO device servers.
spfrx-start: config-spfrx-tango-host ## Start SPFRx TANGO device servers
	@. scripts/spfrx-rxpu-ops.sh up $(SPFRX_ADDRESS) $(SPFRX_BIN) $(SPFRX_TANGO_INSTANCE) $(SPFRX_DEFAULT_LOGGING_LEVEL)

# Call the scripts/spfrx-rxpu-ops.sh script to take DOWN the RXPU
#  This will perform an ssh command to stop the RXPU TANGO device servers.
spfrx-stop: config-spfrx-tango-host ## Stop SPFRx TANGO device servers
	@. scripts/spfrx-rxpu-ops.sh down $(SPFRX_ADDRESS) $(SPFRX_BIN) $(SPFRX_TANGO_INSTANCE) $(SPFRX_DEFAULT_LOGGING_LEVEL)

# Call the scripts/spfrx-host-qsfp-hipower.sh script
#  This will call the bittware function on the local host to engage hi-power mode
spfrx-qsfp-hi-power: ## Set local Bittware to hi-power mode
	@. scripts/spfrx-host-qsfp-hipower.sh ${QSFP_CONTROL_PATH}

ARTIFACTS_POD = $(shell kubectl -n $(KUBE_NAMESPACE) get pod --no-headers --selector=vol=artifacts-admin -o custom-columns=':metadata.name')

x-jive: config-tango-dns  config-spfrx-tango-host ## Run Jive with X11
	@chmod 644 $(HOME)/.Xauthority
	@docker run --rm \
	--network host \
	--env DISPLAY \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	$(ADD_HOSTS) artefact.skatelescope.org/ska-tango-images-tango-jive:7.22.5 &

x-pogo:  ## Run POGO with X11
	@echo DS_XMI=$(DS_XMI)
	@chmod 644 $(HOME)/.Xauthority
	@docker run --rm \
	--network host \
	--env DISPLAY \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	--volume $(PWD)/pogo/$(DS_XMI).xmi:/home/tango/ds/$(DS_XMI).xmi:rw \
	--volume $(PWD)/pogo/SkaMidTalondxHpsBase.xmi:/home/tango/ds/SkaMidTalondxHpsBase.xmi:rw \
	--volume $(PWD)/pogo/.pogorc:/home/tango/.pogorc:rw \
	--volume $(PWD)/pogo/:/home/tango/pogo/:rw \
	--user tango \
	$(ADD_HOSTS) artefact.skatelescope.org/ska-tango-images-tango-pogo:9.6.36 &

run-interactive: config-spfrx-tango-host ## Run docker in interactive mode
	docker run --rm -it \
	--network host \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
    $(strip $(OCI_IMAGE)):$(release) bash

run-interactive-X11: # config-spfrx-tango-host ## Run docker in interactive mode
	docker run --rm -it \
	--network host \
	--env DISPLAY \
	--privileged \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
    $(strip $(OCI_IMAGE)):$(release) bash

config-db: config-spfrx-tango-host ## Configure the database
	@echo Configuring Tango DB at $(SPFRX_TANGO_HOST) with Talon device servers...
	@docker run --rm \
	--network host \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deploy/artifacts:rw \
	$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py --config-db

generate-spfrx-config: ## Generate spfrx-config.json file
	@docker run --rm \
	--network host \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deploy/artifacts:rw \
	$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py --generate-spfrx-config

download-artifacts:  ## Download artifacts from CAR 
	mkdir -p $(SPFRX_LOCAL_DIR)
	@docker run --rm \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deploy/artifacts:rw \
	$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py --download-artifacts

talon-version: config-spfrx-tango-host ## Display SPFRx TANGO device server version information
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	$(strip $(OCI_IMAGE)):$(release) ./spfrx-talondx.py --talon-version

talon-status: config-spfrx-tango-host ## Display SPFRx TANGO device server status information
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--env TERM=xterm \
	$(strip $(OCI_IMAGE)):$(release) ./spfrx-talondx.py --talon-status

spfrx: config-spfrx-tango-host ## SPFRx HPS Console application
	@echo $(Arguments) & \
	docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--user tango \
	$(strip $(OCI_IMAGE)):$(release) ./spfrx.py $(ARGS)

spfrx-deploy: #config-spfrx-tango-host ## SFPRx HPS Deploy application
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--user tango \
	$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py $(ARGS)

spfrx-plotter: config-spfrx-tango-host ## SPFRx Gated Spectrometer GUI application
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--env DISPLAY \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	--user tango \
	$(strip $(OCI_IMAGE))-plot:$(release) ./spfrx_spectrum_plotter.py $(ARGS)

documentation:  ## Re-generate documentation
	cd docs && make clean && make html

help: ## show this help.
	@echo "make targets:"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": .*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: all test help k8s lint logs describe namespace delete_namespace kubeconfig kubectl_dependencies k8s_test install-chart uninstall-chart reinstall-chart upgrade-chart interactive

