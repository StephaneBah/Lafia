# Deploying Lafia

How to put the stack on a server, then keep it up to date. How the deployed system works is in `architecture.md`, section Deployment.

## What you need

- An Ubuntu 24.04 VM with 2 vCPU and 8 GB of memory.
- A firewall (on Azure, the VM's network security group) that admits 80 and 443 from anywhere, and 22 from your own address only. Nothing else.
- A domain with two DNS records pointing at the VM's public IP: `lafia.<domaine>` and the wildcard `*.lafia.<domaine>`. Every application is served on a subdomain of `lafia.<domaine>`.
- The VM's SSH private key, a `.pem` file, on your machine.

The live deployment uses `lafia.stephanebah.page` and the user `azureuser`.

## 1. The SSH key, on Windows

OpenSSH refuses a key that other accounts can read. Keep it in `~/.ssh`, readable by you only, in PowerShell:

```powershell
Copy-Item $HOME\Downloads\<vm-key>.pem $HOME\.ssh\
icacls $HOME\.ssh\<vm-key>.pem /inheritance:r /grant:r "$($env:USERNAME):(R)"
ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine> uname -a    # answers: the key works
```

## 2. Prepare the VM

```sh
ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine>
curl -fsSL https://raw.githubusercontent.com/StephaneBah/Lafia/main/deploiement/preparer-vm.sh | bash -s -- lafia.<domaine>
exit
```

The script installs Docker and starts it at boot, clones the repository into `~/lafia`, and writes `~/lafia/.env`: the domain, a random password for each database (the noyau's and identite's) and a new token key pair. That file never leaves the VM.

Running the script again keeps every value already in `.env` and adds only the variables it lacks. Run it again before deploying a version whose `.env.example` lists a new variable: a database keeps the first password it starts with, so identite's database must never start without its own. `deployer.sh` refuses to deploy while one is missing. On a VM prepared before identite had a database, that is before the first deploy of F2.2:

```sh
ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine> "cd lafia && git pull --ff-only origin main && deploiement/preparer-vm.sh lafia.<domaine>"
```

It prints each variable as kept or added: `IDENTITE_BASE_MOT_DE_PASSE ajoutée`, the others `gardée`.

## 3. Deploy

From your machine, the first time and each time `main` changes:

```sh
ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine> lafia/deploiement/deployer.sh
```

It pulls `main`, checks that `.env` holds every variable of `.env.example`, builds the images one at a time and starts the stack. The first run takes several minutes: every image is built, HAPI creates its schema, and Caddy obtains a certificate for each subdomain.

## 4. Check

- Open `https://soin.lafia.<domaine>`, `https://caisse.…`, `https://pharmacie.…`, `https://citoyen.…`: each page shows its service and the noyau `disponible`.
- Open `https://soin.lafia.<domaine>/connexion` and sign in with one of the demo accounts it lists: the home page names the agent and their établissement.
- On the VM, `docker compose logs chargement` reports the demo dataset loaded: how many resources, how many created by this deploy.
- Run the test suite against the deployment, from your machine. It gets its tokens by signing in with the demo accounts, as a user would: no key leaves the VM.

  ```sh
  LAFIA_DOMAINE=lafia.<domaine> uv run --project tests pytest tests
  ```

  The tests of malformed tokens need the development key, which a deployed stack refuses: they are skipped. So are the network isolation and dataset checks, from your machine. To run those too, run the suite on the VM:

  ```sh
  ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine>
  curl -LsSf https://astral.sh/uv/install.sh | sh    # once
  cd lafia
  LAFIA_DOMAINE=lafia.<domaine> LAFIA_ADRESSE=127.0.0.1 ~/.local/bin/uv run --project tests pytest tests
  ```

  Each run counts about twenty failed sign-ins against the address it runs from, on accounts reserved for the tests; identite refuses an address after 50 within 15 minutes. Leave 15 minutes between a second and a third run from the same machine.

- Reboot once, with `sudo reboot` on the VM or Restart in the Azure portal. A few minutes later the four sites answer again, without anyone logging in.

## When something goes wrong

On the VM, run `docker compose` commands from `~/lafia`.

| Symptom | Likely cause | What to do |
|---|---|---|
| Certificate error in the browser | DNS does not point at the VM yet, or port 80 is closed: Caddy could not prove it owns the name | Check `nslookup soin.lafia.<domaine>` and the firewall, then `docker compose restart passerelle`. `docker compose logs passerelle` shows each attempt. |
| `/api/<acteur>/sante` answers 503 | HAPI is still starting; the first start takes minutes | Wait until `docker compose ps` shows `noyau` healthy. |
| `deployer.sh` stops during `pip install` or `npm ci` | A download failed | Run it again. |
| `deployer.sh` ends on `service "chargement" didn't complete successfully`, and the services do not start | The noyau refused the demo dataset, or did not answer in time | `docker compose logs chargement` names the error. Fix the dataset, or wait for `noyau` to be healthy, then deploy again. |
| `git pull` refuses: "untracked working tree files would be overwritten" | A file was copied onto the VM by hand | Delete that file on the VM, then deploy again. |
| `deployer.sh` stops on `Variables absentes de .env` | This version needs a variable the VM's `.env` lacks | Run `deploiement/preparer-vm.sh lafia.<domaine>` on the VM, then deploy again. |
| `identite` restarts in a loop, its log saying `password authentication failed` | identite's database started with another password than the one now in `.env` | If `.env` gained `IDENTITE_BASE_MOT_DE_PASSE` after the database's first start, identite's data is only accounts, sessions and codes carnet: `docker compose down identite base-identite && docker volume rm lafia_identite-donnees`, then deploy again. Codes carnet issued since are lost. |
| Every sign-in from one machine answers `Trop d'essais` | That address piled up 50 failures within 15 minutes, often from test runs | Wait 15 minutes. |
