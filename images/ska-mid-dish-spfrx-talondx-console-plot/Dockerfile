FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.33 as buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.20

LABEL \
      author="Dave Del Rizzo <Dave.DelRizzo@nrc-cnrc.gc.ca>" \
      description="Mid DISH SPFRx Talon-DX Console Plot Container."

## For tango user, but get access denied when trying to download artifacts via conan
# RUN python -m pip install -r requirements.txt
# COPY conan_local/remotes.json /home/tango/.conan/remotes.json
# RUN sudo chmod +777 -R /home/tango/.conan
# RUN conan remote list

# Since the docker build context is at the root project
# level so the build can access the project dependencies
# (pyproject.toml, poetry.lock)
# we need to set the default directory to be used at
# container launch time to avoid having to access
# scripts through the directories each time
WORKDIR /app/images/ska-mid-dish-spfrx-talondx-console-plot/

USER root

# TODO: temporary; uncomment following lines to fix pip ssl verification issue
################################################################################
# ADD certs /usr/local/share/ca-certificates/
# ENV PIP_CONFIG_FILE pip.conf
# ENV CONAN_CACERT_PATH /usr/local/share/ca-certificates/mda-root-ca.crt
# ENV REQUESTS_CA_BUNDLE /usr/local/share/ca-certificates/mda-root-ca.crt
# RUN update-ca-certificates
################################################################################

# Poetry virtual environment not needed in Docker image
RUN poetry config virtualenvs.create false

RUN pip install --upgrade pip

# Put the project dependency files where they can be found
COPY pyproject.toml poetry.lock /app/

# Get dependencies
RUN poetry export --format requirements.txt --output poetry-requirements.txt --without-hashes --without dev && \
    pip install -r poetry-requirements.txt && \
    rm poetry-requirements.txt

CMD ./spfrx-plotter.py
