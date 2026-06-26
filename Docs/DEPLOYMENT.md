# DermAI — Deployment Guide (Oracle Cloud Always Free + APK)

End state: the **backend + web app** run 24/7 on a free Oracle VM behind **HTTPS** at
a free subdomain, and an installable **Android APK** points at that URL so you can
hand it to a jury/investors who install it and use it from anywhere.

```
 Phone (APK) ─┐                      ┌── serves the web app  (https://DOMAIN/app/)
              ├─► https://DOMAIN ──► Caddy ──► DermAI backend (Docker) ──► Gemini API
 Browser ─────┘   (Let's Encrypt)            (ConvNeXt model, SQLite)
```

You administer the VM from your PC over SSH; the app does **not** run on your PC.

---

## Prerequisites (on your PC)
- An SSH client (Windows 10/11 has `ssh` built in).
- A Google/GitHub account (for the free DuckDNS subdomain) and an Expo account (free, for the APK build).
- The repo is already on GitHub with the model in Git LFS.

---

## Part A — Create the free Oracle VM

1. Sign up at **https://www.oracle.com/cloud/free/** (needs a card for verification; a
   small refundable hold may appear — Always-Free resources are not billed; **do not**
   click "Upgrade to Pay As You Go").
2. Console → **Compute → Instances → Create instance**.
   - **Image:** Canonical **Ubuntu 22.04**.
   - **Shape:** Change → **Ampere (ARM) → VM.Standard.A1.Flex**, set **2 OCPU / 12 GB**
     (well within the Always-Free 4 OCPU / 24 GB).
   - **Add SSH keys:** choose *Generate a key pair* and **download the private key**
     (or paste your own public key).
   - Create. Note the **Public IP address** once it's running.
3. SSH in from your PC (replace the path + IP):
   ```bash
   ssh -i C:\path\to\private-key.key ubuntu@YOUR_PUBLIC_IP
   ```

## Part B — Open the ports

**B1. Oracle firewall (Security List):** Console → your VM → **Virtual Cloud Network**
→ **Security Lists** → Default → **Add Ingress Rules**, source `0.0.0.0/0`, for:
- TCP **80**, TCP **443** (and 22 should already be open).

**B2. Ubuntu's own iptables** (Oracle Ubuntu images block by default) — run on the VM:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## Part C — Free subdomain (DuckDNS)

1. Go to **https://www.duckdns.org**, sign in, create a subdomain, e.g. `dermai`
   → you get **`dermai.duckdns.org`**.
2. Set its **current ip** to your VM's **Public IP** and **update**.
   (DNS now points `dermai.duckdns.org` → your VM.)

## Part D — Install Docker on the VM
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
sudo apt-get install -y git git-lfs
exit            # log out and SSH back in so the docker group applies
```

## Part E — Deploy

```bash
git clone https://github.com/zzaffyy-shaikh/DermAI.git
cd DermAI
git lfs pull                                  # pulls the 106 MB model

cp deploy.env.example .env
nano .env                                     # set DERMAI_DOMAIN, DERMAI_GEMINI_API_KEY,
                                              #     DERMAI_SEED_ADMIN_PASSWORD

docker compose up -d --build                  # first build ~10-15 min on ARM
docker compose logs -f backend                # watch for "classifier ready" / "startup complete"
```

Caddy automatically fetches a TLS certificate (needs Part B/C done first).

## Part F — Verify
- Open **`https://dermai.duckdns.org/`** in a browser → the DermAI web app loads over HTTPS.
- Log in as the admin you set, register a patient, run a screening.

If HTTPS fails: confirm the domain resolves to the VM (`ping dermai.duckdns.org`),
ports 80/443 are open (Parts B1+B2), then `docker compose restart caddy`.

---

## Free, no-card alternative: Hugging Face Spaces

Use this **instead of Parts A–F** if you don't want to use a card. It's $0 forever and
gives you `https://<your-username>-dermai.hf.space`.

> ⚠️ The Space builds by cloning your **GitHub** repo, so your latest code must be
> **pushed to GitHub first** (see "Push the latest code" below).

1. Create a free account at **https://huggingface.co** (email/Google — no card).
2. **New → Space**. Name it `dermai`. **SDK: Docker → Blank**. Visibility: **Public**. Create.
3. In the Space's **Files** tab → **Add file → Create a new file**, and add two files by
   pasting the contents from this repo's `huggingface/` folder:
   - `Dockerfile`  ← from [huggingface/Dockerfile](../huggingface/Dockerfile)
   - `README.md`   ← from [huggingface/README.md](../huggingface/README.md)
4. **Settings → Variables and secrets → New secret**, add:
   - `DERMAI_GEMINI_API_KEY` = your Gemini key
   - `DERMAI_SEED_ADMIN_PASSWORD` = a strong password
5. The Space **builds automatically** (~10–15 min; watch the **Logs** tab). When it shows
   **Running**, open **`https://<your-username>-dermai.hf.space/app/`** → the web app.
6. Continue to **Part G** with `BASE_URL = https://<your-username>-dermai.hf.space`.

**Notes:** free Spaces **sleep when idle** (first load after a nap ~30–60s — open it a
minute before a demo) and storage is **ephemeral** (the admin re-seeds on each boot, but
accounts created mid-session reset if the Space restarts).

---

## Push the latest code (required before any clone-based deploy)

Both Oracle and Hugging Face deploy by cloning your GitHub repo, so the **current code
must be on GitHub** (today's features are not pushed yet):
```bash
git add -A
git commit -m "Deployment config + latest features"
git push
```

---

## Part G — Build the installable APK

1. On your PC, point the app at the deployed backend — edit
   `dermai-rn/src/config.js`:
   ```js
   export const BASE_URL = "https://dermai.duckdns.org";   // no port; Caddy serves 443
   ```
2. Ensure `dermai-rn/app.json` has an Android package id + permissions, and
   `dermai-rn/eas.json` has an APK profile (snippets below — ask me to apply them).
3. Build:
   ```bash
   cd dermai-rn
   npm install -g eas-cli
   eas login
   eas build -p android --profile preview        # produces a downloadable .apk
   ```
4. EAS gives a URL + QR. Download the **.apk**, share it; installers tap it (allow
   "install from unknown sources") and the app talks to your live backend.

### app.json (Android) — required keys
```json
{ "expo": { "android": {
  "package": "com.dermai.app",
  "versionCode": 1,
  "permissions": ["CAMERA", "RECORD_AUDIO", "INTERNET"]
} } }
```
### eas.json — APK profile
```json
{ "build": { "preview": { "android": { "buildType": "apk" } } } }
```

---

## Maintenance & notes
- **Update after code changes:** `git pull && git lfs pull && docker compose up -d --build`.
- **Data persistence:** accounts/DB/uploads persist on Docker volumes. Appointments,
  notifications and diagnosis sessions are **in-memory** and reset on backend restart
  (fine for demos; ask for the Postgres refactor to make them durable).
- **Cost:** $0 on Always Free. Keep the instance lightly busy so Oracle doesn't reclaim it.
- **Security before real users:** rotate the Gemini key, keep `DERMAI_AUTH_MODE=prod`,
  strong admin password (all handled by `.env`).
