FROM bentoml/model-server:0.11.0-py38
MAINTAINER ersilia
RUN pip install rdkit==2023.9.6
RUN conda install -c conda-forge numpy=1.24.4
RUN conda install -c conda-forge curl=8.18.0
RUN pip install rdkit==2023.9.6
RUN pip install tqdm==4.67.1
RUN pip install FPSim2==0.4.5
RUN curl -fsSL https://raw.githubusercontent.com/ersilia-os/eos4qda/main/opam_install.sh | bash


WORKDIR /repo
COPY . /repo
