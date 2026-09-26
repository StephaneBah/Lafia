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

## 2. Prepare the VM, once

```sh
ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine>
curl -fsSL https://raw.githubusercontent.com/StephaneBah/Lafia/main/deploiement/preparer-vm.sh | bash -s -- lafia.<domaine>
exit
```

The script installs Docker and starts it at boot, clones the repository into `~/lafia`, and writes `~/lafia/.env`: the domain, a random database password and a new token key pair. That file never leaves the VM, and running the script again keeps it.

## 3. Deploy

From your machine, the first time and each time `main` changes:

```sh
ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine> lafia/deploiement/deployer.sh
```

It pulls `main`, builds the images one at a time and starts the stack. The first run takes several minutes: every image is built, HAPI creates its schema, and Caddy obtains a certificate for each subdomain.

## 4. Check

- Open `https://soin.lafia.<domaine>`, `https://caisse.…`, `https://pharmacie.…`, `https://citoyen.…`: each page shows its service and the noyau `disponible`.
- On the VM, `docker compose logs chargement` reports the demo dataset loaded: how many resources, how many created by this deploy.
- Run the test suite against the deployment, from your machine. The token key is read from the VM into your shell only:

  ```sh
  export LAFIA_DOMAINE=lafia.<domaine>
  export JETON_CLE_PRIVEE=$(ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine> "grep ^JETON_CLE_PRIVEE= lafia/.env | cut -d= -f2-")
  uv run --project tests pytest tests
  ```

  The network isolation checks are skipped from your machine. To run them too, run the suite on the VM:

  ```sh
  ssh -i ~/.ssh/<vm-key>.pem azureuser@lafia.<domaine>
  curl -LsSf https://astral.sh/uv/install.sh | sh    # once
  cd lafia && set -a && . ./.env && set +a
  LAFIA_ADRESSE=127.0.0.1 ~/.local/bin/uv run --project tests pytest tests
  ```

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
