#!/usr/bin/env bash
# Déploie la branche main sur la VM : tire le dépôt, construit les images, relance la pile.
#
# Depuis son poste, en une commande :
#   ssh -i <clé> azureuser@<domaine> lafia/deploiement/deployer.sh
#
# La VM a été préparée une fois par deploiement/preparer-vm.sh ; son .env reste tel quel.
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --ff-only origin main

# Une image à la fois : sur 2 vCPU, des constructions parallèles se disputent processeur et mémoire,
# et leurs téléchargements simultanés échouent plus souvent. Une image sans construction est sautée.
for service in $(docker compose config --services); do
  docker compose build "$service"
done

# Le premier démarrage du noyau prend quelques minutes : HAPI crée son schéma.
docker compose up -d --wait --remove-orphans
docker image prune -f
docker compose ps
