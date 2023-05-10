#!/usr/bin/env python3
import argparse
import copy
import getpass
import json
import logging
import os
import re
import zipfile
from collections import OrderedDict

import requests
import tango
from conan_local.conan_wrapper import ConanWrapper
from nrcdbpopulate.dbPopulate import DbPopulate
from spfrx_config.talondx_config import TalonDxConfig

LOG_FORMAT = (
    "[spfrx_deployer.py: line %(lineno)s]%(levelname)s: %(message)s"
)


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    OK = "\x1b[6;30;42m"
    FAIL = "\x1b[0;30;41m"
    ENDC = "\x1b[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Version:
    """
    Class to facilitate extracting and comparing version numbers in filenames.

    :param filename: string containing a version substring in the x.y.z
                     format, where x,y,z are numbers.
    """

    def __init__(self, filename):
        [ver_x, ver_y, ver_z] = re.findall("[0-9]+", filename)
        self.X = int(ver_x)
        self.Y = int(ver_y)
        self.Z = int(ver_z)

    def match(self, ver):
        """
        Compare two Version object and return true if the versions match.

        :param ver: Version object being compared to this one.
        """
        return self.X == ver.X and self.Y == ver.Y and self.Z == ver.Z


# POWER_SWITCH_USER = os.environ.get("POWER_SWITCH_USER")
# POWER_SWITCH_PASS = os.environ.get("POWER_SWITCH_PASS")

INTERNAL_BASE_DIR = "/app/images"
OCI_IMAGE_NAME = "ska-mid-dish-spfrx-talondx-console-deploy"
CONFIG_FILE = "spfrx-config.json"
BOARDMAP_FILE = "spfrx_boardmap.json"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(PROJECT_DIR, "artifacts")
SPFRX_CONFIG_FILE = os.path.join(ARTIFACTS_DIR, CONFIG_FILE)
DOWNLOAD_CHUNK_BYTES = 1024

TALONDX_STATUS_OUTPUT_DIR = os.environ.get("TALONDX_STATUS_OUTPUT_DIR")

GITLAB_PROJECTS_URL = "https://gitlab.drao.nrc.ca/api/v4/projects/"
GITLAB_API_HEADER = {
    "PRIVATE-TOKEN": f'{os.environ.get("GIT_ARTIFACTS_TOKEN")}'
}

NEXUS_API_URL = "https://artefact.skatelescope.org/service/rest/v1/"
RAW_REPO_USER = os.environ.get("RAW_USER_ACCOUNT")
RAW_REPO_PASS = os.environ.get("RAW_USER_PASS")


def generate_spfrx_config():
    """
    Reads and displays the state and status of each HPS Tango device
    running on the Talon DX boards, as specified in the configuration
    commands -- ref `"config_commands"`in the spfrx-config JSON file.

    :param boards: Command delimited list of boards to deploy
    """
    with open(
        f"{INTERNAL_BASE_DIR}/{OCI_IMAGE_NAME}/spfrx_config/{BOARDMAP_FILE}",
        "r",
    ) as config_map:
        config_map_json = json.load(config_map)

        spfrx_config_dict = {"ds_binaries": config_map_json["ds_binaries"]}

        spfrx_config_dict = {
            "ds_binaries": config_map_json["ds_binaries"],
        }

        db_servers_list = []
        for db_server in config_map_json["tango-db"]["db_servers"]:
            db_server_tmp = copy.deepcopy(db_server)
            db_servers_list.append(db_server_tmp)

        spfrx_config_dict["tango_db"] = {"db_servers": db_servers_list}
        spfrx_config_file = open(
            f"{INTERNAL_BASE_DIR}/{OCI_IMAGE_NAME}/artifacts/{CONFIG_FILE}",
            "w",
        )
        json.dump(spfrx_config_dict, spfrx_config_file, indent=6)
        spfrx_config_file.close()


def configure_db(
        inputjson
        ) -> None:
    """
    Helper function for configuring DB entries using the dbpopulate module.
    """

    for server in inputjson:
        # TODO: make schema validation part of the dbPopulate class
        # with open( "./schema/dbpopulate_schema.json", 'r' ) as sch:
        with open("nrcdbpopulate/schema/dbpopulate_schema.json", "r") as sch:
            # schemajson = json.load(sch, object_pairs_hook=OrderedDict)
            json.load(sch, object_pairs_hook=OrderedDict)
            sch.seek(0)

        # try:
        #     logger_.info( "Validation step")
        #     jsonschema.validate( server, schemajson )
        # except ValidationError as error:
        #     handleValidationError( error, server )
        #     exit(1)

        dbpop = DbPopulate(server)

        # Remove and add to ensure any previous record is overwritten
        dbpop.process(mode="remove")
        dbpop.process(mode="add")


def configure_tango_db(
        tango_db
        ):
    """
    Configure the Tango DB with devices specified in the talon-config
    JSON file.

    :param tango_db: JSON string containing the device server
                     specifications for populating the Tango DB
    """
    logger_.info("Configure Tango DB")
    configure_db(inputjson=tango_db.get("db_servers", ""))


def download_git_artifacts(
        git_api_url, 
        name
        ):
    response = requests.head(url=git_api_url, headers=GITLAB_API_HEADER)

    if response.status_code == requests.codes.ok:  # pylint: disable=no-member
        total_bytes = int(response.headers["Content-Length"])

        response = requests.get(
            git_api_url, headers=GITLAB_API_HEADER, stream=True
        )

        ds_artifacts_dir = os.path.join(ARTIFACTS_DIR, name)
        filename = os.path.join(ds_artifacts_dir, "artifacts.zip")
        bytes_downloaded = 0
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as fd:
            for chunk in response.iter_content(
                chunk_size=DOWNLOAD_CHUNK_BYTES
            ):
                fd.write(chunk)
                bytes_downloaded = min(
                    bytes_downloaded + DOWNLOAD_CHUNK_BYTES, total_bytes
                )
                per_cent = round(bytes_downloaded / total_bytes * 100.0)
                logger_.debug(
                    f"Downloading {total_bytes} bytes to "
                    f"{os.path.relpath(filename, PROJECT_DIR)} "
                    f"[{bcolors.OK}{per_cent:>3} %{bcolors.ENDC}]",
                    end="\r",
                )
            logger_.info("")

        logger_.info("Extracting files... ", end="")
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall(ds_artifacts_dir)
        logger_.info(f"{bcolors.OK}done{bcolors.ENDC}")
    else:
        logger_.info(
            f"{bcolors.FAIL}status: {response.status_code}{bcolors.ENDC}"
        )


def download_ds_binaries(
        ds_binaries, 
        clear_conan_cache=True
        ):
    """
    Downloads and extracts Tango device server (DS) binaries from
    Conan packages or Git pipeline artifacts.

    :param ds_binaries: JSON string specifying which DS binaries to download.
    :param clear_conan_cache: if true, Conan packages are fetched from
                              remote; default true.
    """
    conan = ConanWrapper(ARTIFACTS_DIR)
    logger_.info(f"Conan version: {conan.version()}")
    if clear_conan_cache:
        logger_.info(f"Conan local cache: {conan.search_local_cache()}")
        logger_.info(
            f"Clearing Conan local cache... {conan.clear_local_cache()}"
        )
    logger_.info(f"Conan local cache: {conan.search_local_cache()}")

    for ds in ds_binaries:
        logger_.info(f"DS Binary: {ds['name']}")

        if ds.get("source") == "conan":
            # Download the specified Conan package
            conan_info = ds.get("conan")
            logger_.info(f"Conan info: {conan_info}")
            conan.download_package(
                pkg_name=conan_info["package_name"],
                version=conan_info["version"],
                user=conan_info["user"],
                channel=conan_info["channel"],
                profile=os.path.join(
                    conan.profiles_dir, conan_info["profile"]
                ),
            )
        elif ds.get("source") == "git":
            # Download the artifacts from the latest successful pipeline
            git_info = ds.get("git")
            url = (
                f'{GITLAB_PROJECTS_URL}{git_info["git_project_id"]}'
                f"/jobs/artifacts/"
                f'{git_info["git_branch"]}/download?job='
                f'{git_info["git_pipeline_job"]}'
            )
            download_git_artifacts(git_api_url=url, name=ds["name"])
        else:
            logger_.info(f'Error: unrecognized source ({ds.get("source")})')
            exit(-1)

    # Modify the permissions of Artifacts dir so they can be
    # modified/deleted later
    chmod_r_cmd = "chmod -R o=rwx " + ARTIFACTS_DIR
    os.system(chmod_r_cmd)


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    logger_ = logging.getLogger("spfrx_deployer.py")
    logger_.info(f"User: {getpass.getuser()}")
    parser = argparse.ArgumentParser(
        description="MID DISH SPFRx Talon-DX Deployer Utility"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true",
    )
    parser.add_argument(
        "--config-db",
        help=f"configure the Tango database with devices specified"
        f" in {BOARDMAP_FILE} file",
        action="store_true",
    )
    parser.add_argument(
        "--generate-spfrx-config",
        help="Generate SPFRx config file",
        action="store_true",
    )
    parser.add_argument(
        "--download-artifacts",
        help="download the Tango DS binaries from the SKA CAR",
        action="store_true",
    )
    args = parser.parse_args()

    if args.config_db:
        logger_.info(
            f"Configure DB - TANGO_HOST = "
            f'{tango.ApiUtil.get_env_var("TANGO_HOST")}'
        )
        config = TalonDxConfig(config_file=SPFRX_CONFIG_FILE)
        configure_tango_db(config.tango_db())
    elif args.download_artifacts:
        logger_.info("Download Artifacts")
        config = TalonDxConfig(config_file=SPFRX_CONFIG_FILE)
        config.export_config(ARTIFACTS_DIR)
        download_ds_binaries(config.ds_binaries())
    elif args.generate_spfrx_config:
        logger_.info("Generate spfrx-config.json file")
        generate_spfrx_config()
    else:
        logger_.info("Hello from Mid DISH SPFRx Deployer")
