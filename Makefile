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

# Set this environment variable to one of the two following values to choose 
# the flavour of supporting software
#   standalone : will require specification of a standalone TANGO DB
#   cluster : (default) will require specification of k8s namespace information
SPFRX_MODE ?= cluster

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= mid-psi-ska-dish-lmc

# SPFRX_TANGO_DOMAIN defines the default domain name for the TANGO DB. This is used
# in constructing the TANGO_HOST for k8s operating mode
SPFRX_TANGO_DOMAIN ?= cluster.local

# SPFRX_ADDRESS is the default IP address for the target Talon-DX board
SPFRX_ADDRESS ?= 192.168.8.200

# SPFRX_STANDALONE_DB_IP is the default IP address for a standalone TANGO DB IP address
SPFRX_STANDALONE_DB_IP ?= 10.165.3.22

# SPFRX_TANGO_INSTANCE is the default instance name for the SPFRx operational registered
# device servers within the TANGO DB
SPFRX_TANGO_INSTANCE ?= spfrx-20

# SPFRX_DEFAULT_LOGGING_LEVEL is the default logging level that all devices servers are
# initiated with
SPFRX_DEFAULT_LOGGING_LEVEL ?= 4

# SPFRX_BIN is the default area for executable binaries and scripts. This default 
# folder should be included in the Talon-DX OS PATH environment variable
SPFRX_BIN ?= /usr/local/bin

# SPFRX_TANGO_PORT is the default TANGO port number used for the TANGO DB
SPFRX_TANGO_PORT ?= 10000

# QSFP_CONTROL_PATH is the default absolute path for qsfp control applications. This 
# should only ever be used when operating in standalone mode.
QSFP_CONTROL_PATH ?= /usr/share/bittware/520nmx/cots/utilities/qsfp_control/bin

# SPFRX_FAN_SPEED is the default PWM fan speed value (maximum)
SPFRX_FAN_SPEED ?= 255

# SPFRX_BSP_HWMON is the default HWMON index to use when searching for device driver
# subfolders
SPFRX_BSP_HWMON ?= 1

# RELEASE_NAME is the release that all Kubernetes resources will be labelled
# with
RELEASE_NAME ?= test

# OCI_IMAGES are the names of the OCI images found within this image repository
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

# The default location of the users local .Xauthoriy file
XAUTHORITY ?= $(HOME)/.Xauthority

# The local hostname
THIS_HOST := $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)

# The local DISPLAY variable
DISPLAY ?= $(THIS_HOST):0

JIVE ?= true# Enable jive
WEBJIVE ?= false# Disable Webjive

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

# Derive the SPFRX Database Pod from the specified KUBE_NAMESPACE
SPFRX_DATABASE_POD = $(shell kubectl get svc -n $(KUBE_NAMESPACE) | grep databaseds | cut -d ' ' -f1)

# Note that for now, the DISH LMC is deployed to SPFRX_TANGO_HOST=192.168.128.68:10000
ifeq ($(SPFRX_MODE),cluster)
# Derive the SPFRX_TANGO_HOST IP address and port number for CLUSTER mode 
#  The format should be:
#   TANGO_HOST=databaseds-tango-base.ci-ska-skampi-cbf-automated-pipeline-testing-mid.svc.cluster.local:10000
	SPFRX_TANGO_HOST ?= $(SPFRX_DATABASE_POD).$(KUBE_NAMESPACE).svc.$(SPFRX_TANGO_DOMAIN):$(SPFRX_TANGO_PORT)
else
# Derive the SPFRX_TANGO_HOST IP address and port number for STANDALONE mode
#  The format should be:
#   TANGO_HOST=spfrx_standalone_db_ip:spfrx_tango_port
	SPFRX_TANGO_HOST ?= $(SPFRX_STANDALONE_DB_IP):$(SPFRX_TANGO_PORT)
endif

run:  ## Run docker container
	docker run --rm $(strip $(OCI_IMAGE)):$(release)

# overwrite to use a different JSON
SPFRX_CONFIG_FILE := spfrx-config-spfrx001.json
SPFRX_CONFIG_FILE_PATH = $(IMG_DIR)/spfrx_config/$(SPFRX_CONFIG_FILE)
SPFRX_LOCAL_DIR = $(PWD)/mnt/spfrx-config
MNT_LOCAL_DIR = $(PWD)/mnt/

spfrx-login: ## login to the current SPFRX_IP as root
	ssh root@$(SPFRX_ADDRESS)

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/config-spfrx-tango-host.sh script
#  This will set the TANGO_HOST environment variable on the specified remote host
#  The format should be:
#   TANGO_HOST=databaseds-tango-base.ci-ska-skampi-cbf-automated-pipeline-testing-mid.svc.cluster.local:10000
#  or similar, depending on the k8s configuration
config-spfrx-tango-host: ## Set TANGO_HOST on SPFRx HPS
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/config-spfrx-tango-host.sh $(SPFRX_ADDRESS) $(SPFRX_TANGO_HOST)

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-deploy-artifacts.sh script
#  This will copy required shell scripts to the specified remote SPFRx HPS host
spfrx-deploy-artifacts: ## Deploy SPFRx artefacts to HPS
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-deploy-artifacts.sh $(SPFRX_ADDRESS) $(SPFRX_LOCAL_DIR) $(SPFRX_BIN)

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-rxpu-ops.sh script to bring UP the RXPU
#  This will perform an ssh command to start the RXPU TANGO device servers.
spfrx-start: ## Start SPFRx TANGO device servers
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-remote-start.sh ${SPFRX_TANGO_HOST} $(SPFRX_ADDRESS) $(SPFRX_BIN) $(SPFRX_TANGO_INSTANCE) $(SPFRX_DEFAULT_LOGGING_LEVEL) &

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-rxpu-ops.sh script to take DOWN the RXPU
#  This will perform an ssh command to stop the RXPU TANGO device servers.
spfrx-stop: ## Stop SPFRx TANGO device servers
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-remote-stop.sh $(SPFRX_ADDRESS) $(SPFRX_BIN)

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-host-qsfp-hipower.sh script
#  This will call the bittware function on the local host to engage hi-power mode
spfrx-qsfp-hi-power: ## Set local Bittware to hi-power mode
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-host-qsfp-hipower.sh ${QSFP_CONTROL_PATH}

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-get-fanspeed.sh script
#  This will return PWM fan settings for fans 1, 2 and 3
#  use SPFRX_BSP_HWMON=# to provide the hwmon index if required (default SPFRX_BSP_HWMON is 1)
spfrx-get-fanspeed: ## Retrieve fan speed settings for RXPU
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-get-fanspeed.sh ${SPFRX_ADDRESS} ${SPFRX_BSP_HWMON}

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-set-fanspeed.sh script
#  This will return PWM fan settings for fans 1, 2 and 3
#  use SPFRX_FAN_SPEED=### to indicate the speed 
#  use SPFRX_BSP_HWMON=# to provide the hwmon index if required (default SPFRX_BSP_HWMON is 1)
spfrx-set-fanspeed: ## Set fan speed settings for RXPU
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/spfrx-set-fanspeed.sh ${SPFRX_ADDRESS} ${SPFRX_FAN_SPEED} ${SPFRX_BSP_HWMON}

# Call the images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/program-bitstream-remote script
#  This will program the bitstream remotely on the SPFRx TALON-DX HPS
spfrx-program-bitstream: ## Remotely configure the SPFRx FPGA
	@. images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/program-bitstream-remote.sh ${ARCHIVE_FILE} ${SPFRX_ADDRESS}

ARTIFACTS_POD = $(shell kubectl -n $(KUBE_NAMESPACE) get pod --no-headers --selector=vol=artifacts-admin -o custom-columns=':metadata.name')

get-namespaces: ## Display kubectl namespaces on local server
	@kubectl get namespaces

get-svc: ## Display kubectl namespace addresses on local server
	@kubectl get svc -n ${KUBE_NAMESPACE}

display-spfrx-database-pod: ## Display the derived SPFRX_DATABASE_POD environment variable
	@echo "SPFRX_DATABASE_POD = ${SPFRX_DATABASE_POD}"

display-spfrx-tango-host: ## Display the SPFRX_TANGO_HOST value
	@echo "SPFRX_TANGO_HOST = ${SPFRX_TANGO_HOST}"

x-jive: config-spfrx-tango-host ## Run Jive with X11
	@chmod 644 $(HOME)/.Xauthority
	@docker run --rm \
	--network host \
	--env DISPLAY \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	artefact.skao.int/ska-tango-images-tango-jive:7.22.5 &

x-pogo:  ## Run POGO with X11
	@chmod 644 $(HOME)/.Xauthority
	@docker run --rm \
	--network host \
	--env DISPLAY \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	--volume $(PWD)/pogo/.pogorc:/home/tango/.pogorc:rw \
	--volume $(PWD):/home/tango/pogo/:rw \
	--user tango \
	artefact.skao.int/ska-tango-images-tango-pogo:9.6.36 &

run-interactive: config-spfrx-tango-host ## Run docker in interactive mode
	docker run --rm -it \
	--network host \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
    artefact.skao.int/$(strip $(OCI_IMAGE)):$(release) bash

run-interactive-X11: config-spfrx-tango-host ## Run docker in interactive mode
	docker run --rm -it \
	--network host \
	--env DISPLAY \
	--privileged \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
    artefact.skao.int/$(strip $(OCI_IMAGE)):$(release) bash

config-db: config-spfrx-tango-host ## Configure the database
	@echo Configuring Tango DB at $(SPFRX_TANGO_HOST) with Talon device servers...
	@docker run --rm \
	--network host \
	--env TANGO_HOST=$(SPFRX_TANGO_HOST) \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deploy/artifacts:rw \
	artefact.skao.int/$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py --config-db $(ARGS)

generate-spfrx-config: ## Generate spfrx-config.json file
	@docker run --rm \
	--network host \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deploy/artifacts:rw \
	artefact.skao.int/$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py --generate-spfrx-config $(ARGS)

download-artifacts:  ## Download artifacts from CAR 
	mkdir -p $(SPFRX_LOCAL_DIR)
	@docker run --rm \
	--volume $(SPFRX_LOCAL_DIR):/app/images/$(strip $(OCI_IMAGE))-deploy/artifacts:rw \
	artefact.skao.int/$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py --download-artifacts $(ARGS)

talon-version: config-spfrx-tango-host ## Display SPFRx TANGO device server version information
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	artefact.skao.int/$(strip $(OCI_IMAGE)):$(release) ./spfrx.py --version_tango_all

talon-status: config-spfrx-tango-host ## Display SPFRx TANGO device server status information
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--env TERM=xterm \
	artefact.skao.int/$(strip $(OCI_IMAGE)):$(release) ./spfrx.py --status_tango_all

spfrx: config-spfrx-tango-host ## SPFRx HPS Console application
	@echo $(Arguments) & \
	docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--user tango \
	artefact.skao.int/$(strip $(OCI_IMAGE)):$(release) ./spfrx.py $(ARGS)

spfrx-deploy: config-spfrx-tango-host ## SFPRx HPS Deploy application
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--user tango \
	artefact.skao.int/$(strip $(OCI_IMAGE))-deploy:$(release) ./spfrx_deployer.py $(ARGS)

spfrx-plotter: config-spfrx-tango-host ## SPFRx Gated Spectrometer GUI application
	@docker run --rm \
	--network host \
	--env "TANGO_HOST=$(SPFRX_TANGO_HOST)" \
	--env DISPLAY \
	--volume /tmp/.X11-unix:/tmp/.X11-unix \
	--volume $(HOME)/.Xauthority:/home/tango/.Xauthority \
	--user tango \
	artefact.skao.int/$(strip $(OCI_IMAGE))-plot:$(release) ./spfrx_spectrum_plotter.py $(ARGS)

documentation:  ## Re-generate documentation
	cd docs && make clean && make html

help: ## show this help.
	@echo "make targets:"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": .*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: all test help k8s lint logs describe namespace delete_namespace kubeconfig kubectl_dependencies k8s_test install-chart uninstall-chart reinstall-chart upgrade-chart interactive

