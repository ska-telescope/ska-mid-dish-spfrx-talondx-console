.. doctest-skip-all
.. talondx:


**************************
Talon DX Config
**************************

SpfrxConfig Class
###################
.. autoclass:: talondx_config.talondx_config.TalonDxConfig
    :members:

Schema
###################
.. literalinclude:: ../../images/ska-mid-dish-spfrx-talondx-console/talondx_config/talondx-config-schema.json
    :language: json

**************************
Conan
**************************

ConanWrapper Class
##################

.. autoclass:: conan_local.conan_wrapper.ConanWrapper
    :members:

Conan Profiles
##############

Cross-compiled (HPS) Tango Devices
----------------------------------

.. literalinclude:: ../../images/ska-mid-dish-spfrx-talondx-console/conan_local/conan_profiles/conan_aarch64_profile.txt

Native-compiled (Linux server) Tango Devices
--------------------------------------------

.. literalinclude:: ../../images/ska-mid-dish-spfrx-talondx-console/conan_local/conan_profiles/conan_x86_profile.txt

Conan Remotes
#############
.. literalinclude:: ../../images/ska-mid-dish-spfrx-talondx-console/conan_local/remotes.json

**************************
Talon DX Log Consumer
**************************
The Talon DX Log Consumer is a Tango device intended to run on the host machine that connects
to the Talon-DX boards. This Tango device is set up as a default logging target for all the
Tango device servers running on the HPS of each Talon-DX board. When the HPS device servers
output logs via the Tango Logging Service, the logs get transmitted to this log consumer device
where they get converted to the SKA logging format and outputted once again via the
SKA logging framework. In this way logs from the Talon-DX boards can be aggregated in once
place and eventually shipped to the Elastic framework in the same way as logs from the Mid CBF
Monitor and Control Software (MCS).

Note that eventually this Tango device will be moved to the Mid CBF MCS, and more instances
of the device may be created to provide enough bandwidth for all the HPS device servers.

Connecting from HPS DS to the Log Consumer
##########################################
The Talon-DX boards connect to the host machine (currently known as the Dell Server) over
a single Ethernet connection. The IP address of the Dell Server on this connection is
``169.254.100.88`` and all outgoing traffic from the Talon-DX boards must be addressed to this IP.

When the log consumer starts up on the Dell server, the OmniORB end point (IP address and port) it is assigned
is local to the Dell server (i.e. IP address ``142.73.34.173``, arbitrary port). Since the Talon 
boards are unable to connect to this IP address. we need to manually publish a different
endpoint when starting up the log consumer that is visible to the HPS devices.

The following ORB arguments are used (see the make target ``talondx-log-consumer``):

* ``-ORBendPointPublish giop:tcp:169.254.100.88:60721``: Exposes this IP address and port to all clients of this Tango device. When the HPS device servers contact the database to get the network information of the log consumer, this is the IP address and port that is returned. The IP addresses matches that of the Ethernet connection to the Dell server, allowing the HPS device servers to direct their messages across that interface.
* ``-ORBendPoint giop:tcp:142.73.34.173:60721``: Assigns the IP address and port that the log consumer device is actually running on. This needs to be manually assigned since an iptables mapping rule was created on the Dell server to route any TCP traffic coming in on ``169.254.100.88:60721`` to ``142.73.34.173:60721``.

Some important notes:

* Due to the end point publishing, no Tango devices running on the Dell server will be able to connect to the log consumer (including being able to configure the device from Jive). This is because the published IP address is not accessible on the Dell server. There may be a way to publish multiple endpoints, but this needs further investigation.
* If the log consumer device cannot be started due to an OmniORB exception saying that the end point cannot be created, it is possible that the ``142.73.34.173`` needs to change to something else. It is not yet clear why this can happen. To change it do the following:

  * Remove the ORB arguments from the ``talondx-log-consumer`` make target, and then start the log consumer.
  * Open up Jive and look at what IP address is automatically assigned to the log consumer device. This is the IP address that we now need to use for the endpoint.
  * Find the iptables rule that maps ``169.254.100.88:60721`` to ``142.73.34.173:60721``, and change it to the new IP address.
  * Add the ORB arguments back in, using the correct IP address for the end point.

**************************
Automated Script
**************************
The automated script is a method to deploy the MCS system inside the minikube and execute commands through the engineering console without relying on make commands in a given git repository. All images and containers are pulled directly from CAR.

Preconditions
##########################################
* The script must be run as a user with passwordless root permission.
* The script must be run from the .../automation directory.
* Latest stable MCS and Engineering Console image versions are known hard-coded in script.

Key Files
##########################################

The following files are necessary to run the automated script:

* ``orchestration.sh``: The entry point for a cronjob.

  * Ensures more than one instance of the script is not running.
  * Creates the test result directories.
* ``setup.sh``: Sets up the test environment.

  * Records the test configuration.
  * Starts Minikube.
  * Programs the talon boards.
* ``script.sh.multiboard``: The test. See "Current Outcomes" below.

Current Outcomes
##########################################

Using a git and makefile detached script to automate the following:

* MID CBF MCS Deployment
* Use Engineering Console to:

  * Configure the Tango DB inside MCS
  * Turn on the Talon Boards using the LMC Interface
  * Check the Talon DS Versions to verify status
  * Generate BITE Data
  * Replay the BITE Data through the board back into the primary server
  * Capture the data on the Engineering Console
  * Configure the VCC Bands
  * Use the Serial Loop-back to Send the BITE Data back through the board into the VCC Firmware IP Blocks
  * Use the RDMA Tx to send the VCC Data to the RDMA Rx
* Run the automated script nightly as a regression test.


Future Outcomes
##########################################
The features of the automated script will be extended to the following:

* Verify the data captured by the RDMA Rx

The current automated script is run nightly and saves the test results locally. The aim is to send the results to JIRA X-RAY, as well as to generate reports with captured data and plots.

Running the Script
##########################################
Refer to the `Automated Script Confluence Page <https://confluence.skatelescope.org/display/SE/Eng+Console+Automated+Script+on+Dell+Server>`_
