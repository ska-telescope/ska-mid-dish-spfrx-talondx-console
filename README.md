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

*Note: one may also build a specific container - useful during development*
```
make oci-build --env OCI_IMAGE=<name of container image path>
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


### Generate SPFRx Talon-DX Config FIle
To auto-generate the SPFRx Talon-DX config file based on the board configuration. Run the following command:
```bash
make generate-spfrx-config
```
This will write a new spfrx-config.json file into the local /mnt/spfrx-config folder.


### Download Artefacts from CAR
To download Talon Tango device binaries from CAR to the local folder specified in the Makefile (`SPFRX_TALONDX_DEST_DIR`): 
```bash
make download-artifacts
```
or specify a different destination folder:
```bash
make download-artifacts SPFRX_TALONDX_DEST_DIR="destination-folder"
```
A different config JSON can be specified if it exists as well (default value in the Makefile);
```bash
make download-artifacts
```
This will by default write artifacts into the local /mnt/spfrx-config folder.


### Optional: Override DS Artefacts with local build
In order for this script to work, ensure to clone and build your device servers in the same root directory:
Example: If clone ds-vcc and ds-lstv-gen device servers ensure both are cloned under the same directory which would like like:
1. /home/user/dev/ds/ds-lstv-gen
2. /home/user/dev/ds/ds-vcc

To override the device servers (ds-lstv-gen,ds-vcc in this example) run the following command:
```bash
make ds_list=ds-lstv-gen,ds-vcc ds_basedir=<path to ds base directory> mcs_dir=<path to mcs checkout> ds-override-local
```
where ds_basedir is the path to the device server root directory of clone, /home/user/dev/ds from the previous example 



### Update the TANGO DB inside MCS
```bash
make config-db
```
This command adds the SPFRx Talon-DX device servers as specified in the `spfrx_boardmap.json` file.



### Pull and run the Docker from CAR
```bash
docker pull artefact.skao.int/ska-mid-dish-spfrx-talondx-console:0.0.1
docker run artefact.skao.int/ska-mid-dish-spfrx-talondx-console:0.0.1
```


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

---




