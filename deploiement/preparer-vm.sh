#!/usr/bin/env bash
# Prépare une VM Ubuntu 24.04 neuve pour Lafia, une fois : Docker, le dépôt, et le .env de production.
#
# Sur la VM, depuis le dépôt public :
#   curl -fsSL https://raw.githubusercontent.com/StephaneBah/Lafia/main/deploiement/preparer-vm.sh | bash -s -- <domaine>
# <domaine> est la base des sous-domaines : lafia.exemple.org sert soin.lafia.exemple.org, …
#
# Relancé, il ne refait que ce qui manque. Il ne remplace jamais un .env existant : ses secrets ne
# vivent que sur la VM, et en changer invaliderait la base du noyau et les jetons émis.
set -euo pipefail

DOMAINE="${1:?usage : preparer-vm.sh <domaine>, par exemple lafia.exemple.org}"
DEPOT=https://github.com/StephaneBah/Lafia.git
RACINE="$HOME/lafia"

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

# Le .env de production, lisible par ce seul compte. Clés Ed25519 : la ligne base64 entre les bornes
# de chaque PEM, comme l'attendent les services (JETON_CLE_PUBLIQUE) et la suite de tests (JETON_CLE_PRIVEE).
if [ ! -f "$RACINE/.env" ]; then
  umask 077
  paire=$(mktemp)
  openssl genpkey -algorithm ed25519 -out "$paire"
  cle_privee=$(sed -n 2p "$paire")
  cle_publique=$(openssl pkey -in "$paire" -pubout | sed -n 2p)
  rm -f "$paire"
  cat > "$RACINE/.env" <<ENV
LAFIA_DOMAINE=$DOMAINE
NOYAU_BASE_MOT_DE_PASSE=$(openssl rand -base64 32)
JETON_CLE_PUBLIQUE=$cle_publique
JETON_CLE_PRIVEE=$cle_privee
ENV
  echo ".env écrit pour $DOMAINE : $RACINE/.env"
else
  echo ".env existant gardé : $RACINE/.env"
fi

echo "VM prête. Déployer : $RACINE/deploiement/deployer.sh (après reconnexion, pour docker sans sudo)."
