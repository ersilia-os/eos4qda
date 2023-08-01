FROM bentoml/model-server:0.11.0-py38
MAINTAINER ersilia

RUN pip install rdkit==2023.3.2
RUN sudo apt-get install bubblewrap -y
RUN echo "/usr/local/bin" | sudo bash -c "sh <(curl -fsSL https://raw.githubusercontent.com/ocaml/opam/master/shell/install.sh)" -y
RUN opam init -n; eval `opam env`; opam install fasmifra -y

WORKDIR /repo
COPY . /repo
