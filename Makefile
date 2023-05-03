#
# Project makefile for a Tango project. You should normally only need to modify
# PROJECT below.
#

#
# CAR_OCI_REGISTRY_HOST and PROJECT are combined to define
# the Docker tag for this project. The definition below inherits the standard
# value for CAR_OCI_REGISTRY_HOST = artefact.skao.int and overwrites
# PROJECT to give a final Docker tag of
# artefact.skao.int/ska-tango-examples/powersupply
#
PROJECT = ska-mid-dish-spfrx-talondx-console

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-mid-dish-spfrx
DOMAIN ?= cluster.local

# RELEASE_NAME is the release that all Kubernetes resources will be labelled
# with
RELEASE_NAME ?= test

OCI_IMAGES ?= ska-mid-dish-spfrx-talondx-console ska-mid-dish-spfrx-talondx-console-deployer
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

ITANGO_DOCKER_IMAGE = $(CAR_OCI_REGISTRY_HOST)/ska-tango-images-tango-itango:9.3.5

PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=$(IMG_DIR)

PYTHON_VARS_AFTER_PYTEST = -m "not post_deployment"

# PYTHON_BUILD_TYPE = non_tag_setup

PYTHON_SWITCHES_FOR_FLAKE8 = --ignore=E203,E402,E501,F407,W503

PYTHON_LINT_TARGET = $(IMG_DIR)

MCS_DATABASE_POD = $(shell kubectl get svc -n $(KUBE_NAMESPACE) | grep databaseds | cut -d ' ' -f1)
MCS_TANGO_HOST = $(MCS_DATABASE_POD).$(KUBE_NAMESPACE).svc.$(DOMAIN):10000

run:  ## Run docker container
	docker run --rm $(strip $(OCI_IMAGE)):$(release)

ADD_HOSTS_FILE := $(PWD)/scripts/hosts.out
ADD_HOSTS = $(shell cat $(ADD_HOSTS_FILE))

# overwrite to use a different JSON
SPFRX_CONFIG_FILE := spfrx-config.json
SPFRX_CONFIG_FILE_PATH = $(IMG_DIR)/spfrx_config/$(SPFRX_CONFIG_FILE)
SPFRX_LOCAL_DIR = $(PWD)/mnt/spfrx-config/
MNT_LOCAL_DIR = $(PWD)/mnt/

BOARDS = "2"

HOSTNAME=$(shell hostname)
ifeq ($(HOSTNAME),rmdskadevdu001.mda.ca)
	BITE_IFACE_NAME="ens2f0np0"
	RDMA_IFACE_NAME="ens2f1np1"
else ifeq ($(HOSTNAME),rmdskadevdu002.mda.ca)
	BITE_IFACE_NAME="ens4f0np0"
	RDMA_IFACE_NAME="ens4f1np1"
endif
BITE_MAC_ADDRESS=$(shell ifconfig $(BITE_IFACE_NAME) | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}')
RDMA_IP=$(shell ifconfig $(RDMA_IFACE_NAME) | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*')
RDMA_MAC_ADDRESS=$(shell ifconfig $(RDMA_IFACE_NAME) | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}')
RDMA_MLX=$(shell show_gids | grep v2 | grep $(RDMA_IP) | awk -F ' ' '{print $$1}')
RDMA_GID_IDX=$(shell show_gids | grep v2 | grep $(RDMA_IP) | awk -F ' ' '{print $$3}')

config-tango-dns: ## Create list of additional MCS DS hosts for docker run command
	@. scripts/config-tango-dns.sh $(KUBE_NAMESPACE) $(DOMAIN) $(ADD_HOSTS_FILE)

config-etc-hosts:
	@. scripts/config-etc-hosts.sh $(KUBE_NAMESPACE) $(DOMAIN)

FINAL_DIR_FILE := $(PWD)/scripts/final_dir.out
FINAL_DIR = $(shell cat $(FINAL_DIR_FILE))

ARTIFACTS_POD = $(shell kubectl -n $(KUBE_NAMESPACE) get pod --no-headers --selector=vol=artifacts-admin -o custom-columns=':metadata.name')

capture-datetime-dir:
	@. scripts/create-datetime-dir.sh $(BITE_CAPTURE_LOCAL_DIR) $(FINAL_DIR_FILE)

status-datetime-dir:
	@. scripts/create-datetime-dir.sh $(BITE_STATUS_LOCAL_DIR) $(FINAL_DIR_FILE)

x-jive: config-tango-dns  ## Run Jive with X11
	@chmod 644 $(HOME)/.Xauthority
	@docker run --rm \
	--network host \
	--env DISPLAY \
	--env TANGO_HOST=$(MCS_TANGO_HOST) \
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

run-interactive: config-tango-dns  ## Run docker in interactive mode
	docker run --rm -it \
	--network host \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))/artifacts:rw \
	--env TANGO_HOST=$(MCS_TANGO_HOST) \
	$(ADD_HOSTS) $(strip $(OCI_IMAGE)):$(release) bash

config-db: config-tango-dns copy-artifacts-pod ## Configure the database
	@echo Configuring Tango DB at $(MCS_TANGO_HOST) with Talon device servers...
	@docker run --rm \
	--network host \
	--env TANGO_HOST=$(MCS_TANGO_HOST) \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deployer/artifacts:rw \
	$(ADD_HOSTS) $(strip $(OCI_IMAGE))-deployer:$(release) ./spfrx-deployer.py --config-db

generate-spfrx-config:
	@docker run --rm \
	--network host \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deployer/artifacts:rw \
	$(ADD_HOSTS) $(strip $(OCI_IMAGE))-deployer:$(release) ./spfrx-deployer.py --generate-spfrx-config

download-artifacts:  ## Download artifacts from CAR and copy the on command sequence script
	mkdir -p $(SPFRX_LOCAL_DIR)
	@docker run --rm \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deployer/artifacts:rw \
	$(strip $(OCI_IMAGE))-deployer:$(release) ./spfrx-deployer.py --download-artifacts

talon-version: config-tango-dns
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(MCS_TANGO_HOST)" \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))/artifacts:rw \
	$(ADD_HOSTS) $(strip $(OCI_IMAGE)):$(release) ./spfrx-talondx.py --talon-version

talon-status: config-tango-dns
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(MCS_TANGO_HOST)" \
	--env TERM=xterm \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))/artifacts:rw \
	$(ADD_HOSTS) $(strip $(OCI_IMAGE)):$(release) ./spfrx-talondx.py --talon-status

spfrx-plotter:
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(MCS_TANGO_HOST)" \
	--env DISPLAY \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))/artifacts:rw \
	--user tango \
	$(ADD_HOSTS) $(strip $(OCI_IMAGE)):$(release) ./spfrx-spectrum-plotter.py --plotter_version

documentation:  ## Re-generate documentation
	cd docs && make clean && make html

help: ## show this help.
	@echo "make targets:"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": .*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: all test help k8s lint logs describe namespace delete_namespace kubeconfig kubectl_dependencies k8s_test install-chart uninstall-chart reinstall-chart upgrade-chart interactive

