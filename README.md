# SKA Mid Dish SPFRx Talon-DX

Code repository: [ska-mid-dish-spfrx-talondx-console](https://gitlab.com/ska-telescope/ska-mid-dish-spfrx-talondx-console)

The SPFRx Talon-DX Console is being built in a Docker container, which insulates it from variations in the server environment. 

The SPFRx Talon-DX Console Docker is built in the pipeline and deployed to the Central Artefact Repository [CAR](https://artefact.skatelescope.org/#browse/browse:docker-internal:v2%2Fska-mid-dish-spfrx-talondx-console).


## Installation
```bash
git clone https://gitlab.com/ska-telescope/ska-mid-dish-spfrx-talondx-console
cd ska-mid-dish-spfrx-talondx-console
git submodule init
git submodule update
poetry install # to create the virtual environment with all dependencies
poetry shell # to run shell in the virtual environment
make oci-build # or "poetry run make oci-build" if not in the poetry shell
make run    # runs "hello world" test
```

*Note: one may build all containers with the same command*
```
make oci-build-all
```
*or build a specific container - useful during development*
```
make oci-build --env OCI_IMAGE=<name of container image path>
```

## Development
To run the lint command:
```
make python-lint
```

## Usage
### Run the Docker interactively
To run the docker interactively:
```bash
make run-interactive
```
which opens a bash shell in the docker. 
To see available test script options: 
```bash
./spfrx-talondx.py --help
```
To install vim/nano editors while in interactive mode:
```
apt-get update
apt-get -y install vim nano
```

## LMC Status Targets
The top-level Makefile provides a few handy targets to check status of the LMC namespace and database:

```bash
make get-namespace
make get-svc
make display-spfrx-database-pod
make display-spfrx-tango-host
```
These commands will report on the namespaces currently existing in the environment, as well as show the status and IP addresses of the TANGO DB svc within the defined **KUBE_NAMESPACE**. Override the **KUBE_NAMESPACE** on the command line like this:
```bash
make get-svc KUBE_NAMESPACE=my-namespace
```

The **SPFRX_DATABASE_POD** environment variable is defined by using **KUBE_NAMESPACE** in a call to ***kubestl get_svc*** in order to assemble an IP address name to access the LMC TANGO Database within a k8s cluster. This variable is only used if **SPFRX_MODE** is set to ***cluster*** (the default).


## SPFRx-Specific Console Operations


### Modify/Update the Makefile
Many targets exist in the local Makefile to allow users to perform SPFRx console operations on the command line. For any given specific installation of the SPFRx console, the Makefile in the top level of this repository can be modified to reflect the specific configuration of the local system. In particular, the following environment variables can be updated:

The following environment variables are set conditionally within the Makefile, allowing them to be overridden on the command line for convenience.

**SPFRX_MODE** : indicates where the Makefile expects the TANGO DB to be found. By default this is set to ***cluster***, which indicates the Tango DB is expected to be contained within an LMC-based k8s cluser, the namespace of which is identified by ***KUBE_NAMESPACE***, a value defined within the Makefile.

**KUBE_NAMESPACE** : provides the default namespace for the LMC within a k8s cluster. Defaults to ***mid-psi-ska-dish-lmc***. The IP address of the TANGO DB is assembled using this value, if the ***SPFRX_MODE*** is set to ***cluster***.

**SPFRX_TANGO_DOMAIN** : provides the default domain name for the TANGO DB, used in assembling the ***TANGO_HOST*** variable when ***SPFRX_MODE*** is set to ***cluster***.

**SPFRX_ADDRESS** : the IPv4 address of the target SPFRx Talon-DX HPS computer within the RXPU. The default is set to ***192.168.8.200***, the IP address of the SPFRx Talon-DX HPS in the PSI.

**SPFRX_STANDALONE_DB_IP** : provides an IPv4 address at which a standalone TANGO DB is hosted. This is used when ***SPFRX_MODE*** is anything other than ***cluster*** in assembling the ***TANGO_HOST*** variable.

**SPFRX_TANGO_INSTANCE** : provides a default TANGO instance value used when starting device servers on the SPFRx RXPU. This defaults to ***spfrx-20*** and should be changed in the Makefile, or overridden based on the configuration found in the spfrx_boardmap configuration JSON used. 

**SPFRX_DEFAULT_LOGGING_LEVEL** : provides a default logging level used when starting SFPRx device servers. This defaults to ***4 (INFO)***.

**SPFRX_BIN** : provides an absolute path within the SFPRx HPS operting system where executable artifacts are deployed. This path should be in the system path for the root user on the SPFRx HPS. Defaults to ***/usr/local/bin***.

**SPFRX_TANGO_PORT** : provides a port number on which the TANGO DB is connected. This defaults to ***10000***, the standard TANGO DB port.

The **SPFRX_TANGO_HOST** environment variable is conditionally set within the Makefile in one of two ways, depending on the ***SPFRX_MODE*** (which defaults to ***cluster***). This may be overridden on the command line if required.


### Generate SPFRx Talon-DX Config FIle
To auto-generate the SPFRx Talon-DX config file based on the board configuration found in the spfrx_boardmap JSON file, run the following command:
```bash
make generate-spfrx-config
```
This will write a new spfrx-config.json file into the local /mnt/spfrx-config folder. to view the options that can be specified on the command line, issue the following:
```bash
make generate-spfrx-config ARGS="--help"
```
Any argument available within the ***spfrx-deployer.py*** module may be supplied to this target by providing the arguments within the ***ARGS*** environment variable in the same fashion.


### Download Artefacts from CAR
To download Talon TANGO device binaries from CAR to the local artifacts folder that is mounted within the deploy container (***mnt/spfrx-config***)  
```bash
make download-artifacts
```
The user may specify a differnt boardmap JSON if it exists as well. The default value in the spfrx_deployer.py module is ***spfrx_boardmap_ska001.json*** located in the ***images/ska-mid-dish-spfrx-talondx-console-deploy/spfrx_config*** directory in this repository.
```bash
make download-artifacts ARGS="--boardmap_file NAME-OF-BOARDMAP-FILE.json"
```
This will by default write artifacts into the local ***/mnt/spfrx-config*** directory.


### Update the TANGO DB inside LMC cluster (or standalone DB)
In order for the TANGO devices to work, they require access to an operational TANGO DB. Configure the TANGO DB with the following make target:
```bash
make config-db
```
This command adds the SPFRx Talon-DX device servers as specified in the generated SPFRx configuration file specified in the boardmap. Several arguments can be overridden with this request as follows:
```bash
make config-db SPFRX_TANGO_HOST=TANGO-HOST-IP ARGS="--config-file SPFRX-CONFIG-FILE"
```

### Deploy artefacts to the SFPRX Talon-DX HPS
This make target copies artefacts from the ***mnt/spfrx-config*** environment to the SPFRX Talon-DX board, specifically into the ***/usr/local/bin*** folder, which is in the path for the root user. This renders all uploaded artefacts executable from anywhere on the system. This target runs a script found in the ***images/ska-mid-dish-spfrx-talondx-console-deploy/scripts*** directory.
```bash
make spfrx-deploy-artifacts
```
This script uses default make environment variables ***SPFRX_ADDRESS***, ***SPFRX_LOCAL_DIR***, and ***SPFRX_BIN***, which may all be overridden on the command line as such:
```bash
make spfrx-deploy-artifacts SPFRX_ADDRESS=IP-ADDRESS SPFRX_LOCAL_DIR=LOCAL-DIRECTORY-WHERE-ARTEFACTS-RESIDE SPFRX_BIN=DIRECTORY-ON-TALON-WHERE-ARTEFACTS-ARE-COPIED-TO
```


### Program the SPFRx Bitstream
Once power has been applied to the SPFRx RXPU, and the OS has booted, the user is required to program the bitstream into the FPGA. This operation requires access to a ***tar.gz*** file containing various bitstream configuration files required to configure the FPGA. Program the bitstream using the following make target:
```bash
make spfrx-program-bitstream ARCHIVE_FILE=ABSOLUTE-PATH-TO-BITSTREAM-ARCHIVE-FILE SPFRX_ADDRESS=IP-ADDRESS-OF-SPFRx-TALON-HPS
```
No default ***ARCHIVE_FILE*** is defined within the Makefile, however there is a default ***SPFRX_ADDRESS*** defined, and this argument may be omitted if the value is correct.
This target runs a script in the ***images/ska-mid-dish-spfrx-talondx-console-deploy/scripts*** directory that unpacks certain files from the ARCHIVE_FILE and copies them over to the SPFRx Talon-DX HPS.
The result of this operation is the output of 10 dmesg files, which will indicate that the programming of the FPGA was successful.


### Start/Stop the Controller and Device Servers for SPFRx
These operations can be performed from the host machine by issuing the following make targets:
```bash
make spfrx-start
make spfrx-stop
```
Each target accesses executable scripts that should have already been deployed to the SPFRx Talon-DX HPS. Each target makes use of default environment variables defined within the Makefile, any of which can be overridden on the command line:
```bash
make spfrx-start SPFRX_TANGO_HOST=TANGO-DB-IP-and-PORT SPFRX_ADDRESS=SPFRX-IP-ADDRESS SPFRX_BIN=DIR-LOCATION-OF-EXECUTABLES-ON-TALON SPFRX_TANGO_INSTANCE=INSTANCE-NAME-AS-DEFINED-IN-BOARDMAP SPFRX_DEFAULT_LOGGING_LEVEL=LOGGING-LEVEL
```
and 
```bash
make spfrx-stop SPFRX_ADDRESS=SPFRX-IP-ADDRESS SPFRX_BIN=DIR-LOCATION-OF-EXECUTABLES-ON-TALON
```
The device servers are all defined to have logs sent to the LMC logging device, as well as to the console::cout, so all log messages should be visible when these targets are executed.


## Ancillary make targets

Some makefile targets are supplied for convenience.

```bash
make spfrx-qsfp-hi-power
```
Used in the case where a bittware card provide CSP surrogate capabilities to the SPFRx (ie. @ SARAO). Issuing this target drives the bittware card into hi-power mode, and makes use of the default ***QSFP_CONTROL_PATH*** variable in the Makefile, which may be overridden on the command line.

```bash
make spfrx-get-fanspeed SPFRX_ADDRESS=IP-ADDRESS SPFRX_BSP_HWMON=hwmon-value
make spfrx-set-fanspeed SPFRX_ADDRESS=IP-ADDRESS SPFRX_FAN_SPEED=SPEED SPFRX_BSP_HWMON=hwmon-value
```
These targets get and set the fan speed of the RXPU and are provided as a convenience to the user. All variables listed above have defaults conditionally defined in the Makefile - except for ***SPFRX_FAN_SPEED*** in the spfrx-set-fanspeed target.
The fan speed provided should be an integer between 1 and 255, and translates to the PWM value for all 3 fans simultaneously.


## Read the Docs
The SPFRX Talon-DX Console project auto-generates [Read the Docs](https://developer.skao.int/projects/ska-mid-dish-spfrx-talondx-console/en/latest/) documentation, which includes this README.

To re-generate the documentation locally prior to checking in updates to Git:
```bash
make documentation
```
To see the generated documentation, open `/ska-mid-dish-spfrx-talondx-console/docs/build/html/index.html` in a browser -- e.g.,
```
firefox docs/build/html/index.html &
```




