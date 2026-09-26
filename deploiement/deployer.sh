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

# Chaque variable de .env.example doit être dans .env : une base démarrée sans son mot de passe
# garderait celui de développement. preparer-vm.sh ajoute celles qui manquent, sans toucher aux autres.
manquantes=$(grep -oE '^[A-Z_]+=' .env.example | while read -r variable; do
  grep -q "^$variable" .env || echo "${variable%=}"
done)
if [ -n "$manquantes" ]; then
  echo "Variables absentes de .env : $manquantes. Lancer d'abord deploiement/preparer-vm.sh <domaine>." >&2
  exit 1
fi

# Une image à la fois : sur 2 vCPU, des constructions parallèles se disputent processeur et mémoire,
# et leurs téléchargements simultanés échouent plus souvent. Une image sans construction est sautée.
for service in $(docker compose config --services); do
  docker compose build "$service"
done

# Le premier démarrage du noyau prend quelques minutes : HAPI crée son schéma.
docker compose up -d --wait --remove-orphans

# La passerelle monte le Caddyfile fichier par fichier : git le remplace par un nouveau fichier, qu'elle
# ne voit qu'une fois recréée. Elle l'est quand le Caddyfile qu'elle sert diffère de celui du dépôt.
if ! docker compose exec -T passerelle cat /etc/caddy/Caddyfile | cmp -s - Caddyfile; then
  docker compose up -d --wait --force-recreate --no-deps passerelle
fi

docker image prune -f
docker compose ps
