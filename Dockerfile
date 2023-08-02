FROM bentoml/model-server:0.11.0-py38
MAINTAINER ersilia

RUN pip install rdkit==2023.3.2
RUN sudo apt update
RUN sudo apt-get install bubblewrap -y
RUN sudo apt-get install librdkit-dev python3-rdkit -y
RUN echo "/usr/local/bin" | sudo bash -c "sh <(curl -fsSL https://raw.githubusercontent.com/ocaml/opam/master/shell/install.sh)" -y
RUN echo "N N" | opam init; eval `opam env`; opam install fasmifra -y

WORKDIR /repo
COPY . /repo
