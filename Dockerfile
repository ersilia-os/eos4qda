FROM bentoml/model-server:0.11.0-py38
LABEL maintainer="ersilia"

ENV DEBIAN_FRONTEND=noninteractive
ENV OPAMYES=1

# Use bash so `eval "$(opam env)"` works reliably
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy the installer first (so it can leverage Docker layer caching)
COPY opam_install.sh /usr/local/bin/opam_install.sh
RUN chmod +x /usr/local/bin/opam_install.sh && /usr/local/bin/opam_install.sh

# Python deps in one layer
RUN pip install --no-cache-dir tqdm==4.67.1 FPSim2==0.4.5

WORKDIR /repo
COPY . /repo
