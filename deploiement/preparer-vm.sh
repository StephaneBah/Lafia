#!/usr/bin/env bash
# Prépare une VM Ubuntu 24.04 pour Lafia : Docker, le dépôt, et le .env de production.
#
# Sur la VM, depuis le dépôt public :
#   curl -fsSL https://raw.githubusercontent.com/StephaneBah/Lafia/main/deploiement/preparer-vm.sh | bash -s -- <domaine>
# <domaine> est la base des sous-domaines : lafia.exemple.org sert soin.lafia.exemple.org, …
#
# Relancé, il ne refait que ce qui manque. Il ne remplace jamais une valeur du .env : ses secrets ne
# vivent que sur la VM, et en changer invaliderait les bases et les jetons émis. Il ajoute seulement
# les variables qui y manquent : le relancer avant de déployer une version qui en demande une nouvelle.
# PostgreSQL garde le premier mot de passe qu'il reçoit : une base démarrée sans le sien garderait
# celui de développement.
set -euo pipefail

DOMAINE="${1:?usage : preparer-vm.sh <domaine>, par exemple lafia.exemple.org}"
DEPOT=https://github.com/StephaneBah/Lafia.git
RACINE="$HOME/lafia"
ENV="$RACINE/.env"

# Docker Engine et Compose, depuis le dépôt apt de Docker.
if ! command -v docker >/dev/null; then
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -q
  sudo apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
# Docker démarre avec la VM ; les conteneurs, en restart: unless-stopped, repartent avec lui.
sudo systemctl enable --now docker
# docker sans sudo, dès la prochaine connexion.
sudo usermod -aG docker "$USER"

if [ ! -d "$RACINE/.git" ]; then
  git clone "$DEPOT" "$RACINE"
fi

# Le .env de production, lisible par ce seul compte.
umask 077
touch "$ENV"

a_la_variable() {
  grep -q "^$1=" "$ENV"
}

# Ajoute `variable=valeur` au .env, sauf si la variable y est déjà : sa valeur reste celle d'avant.
ajouter_si_absente() {
  if a_la_variable "$1"; then
    echo "$1 gardée"
  else
    echo "$1=$2" >> "$ENV"
    echo "$1 ajoutée"
  fi
}

ajouter_si_absente LAFIA_DOMAINE "$DOMAINE"
ajouter_si_absente NOYAU_BASE_MOT_DE_PASSE "$(openssl rand -base64 32)"
ajouter_si_absente IDENTITE_BASE_MOT_DE_PASSE "$(openssl rand -base64 32)"

# La paire de clés des jetons, écrite ensemble ou pas du tout : la ligne base64 entre les bornes de
# chaque PEM, comme les lisent identite (JETON_CLE_PRIVEE) et les services (JETON_CLE_PUBLIQUE).
if a_la_variable JETON_CLE_PRIVEE && a_la_variable JETON_CLE_PUBLIQUE; then
  echo "JETON_CLE_PRIVEE et JETON_CLE_PUBLIQUE gardées"
elif a_la_variable JETON_CLE_PRIVEE || a_la_variable JETON_CLE_PUBLIQUE; then
  echo "$ENV ne tient qu'une des deux clés des jetons : corriger à la main." >&2
  exit 1
else
  paire=$(mktemp)
  openssl genpkey -algorithm ed25519 -out "$paire"
  echo "JETON_CLE_PUBLIQUE=$(openssl pkey -in "$paire" -pubout | sed -n 2p)" >> "$ENV"
  echo "JETON_CLE_PRIVEE=$(sed -n 2p "$paire")" >> "$ENV"
  rm -f "$paire"
  echo "JETON_CLE_PRIVEE et JETON_CLE_PUBLIQUE ajoutées"
fi

echo "VM prête. Déployer : $RACINE/deploiement/deployer.sh (après reconnexion, pour docker sans sudo)."
