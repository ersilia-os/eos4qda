FROM bentoml/model-server:0.11.0-py38
MAINTAINER ersilia

RUN curl -fsSL https://raw.githubusercontent.com/ersilia-os/eos4qda/main/opam_install.sh | bash
RUN pip install tqdm==4.67.1
RUN pip install FPSim2==0.4.5

WORKDIR /repo
COPY . /repo