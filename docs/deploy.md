# Accounts & Deployment

## How accounts work
- No public sign-up. An admin creates each player in **Admin → Accounts** and sends them their username + temporary
  password; players can change it from the name menu (top right).
- Admins: post the week's lines (upload the sheet on the Picks tab; saving posts it for everyone), override deadlines,
  set per-player adjustments/penalties, unlock a player's week past the deadline, manage accounts, post an
  announcement, and download/restore backups.
- Regular players: make and save their own picks, copy the email, see their own stats.

## Deadlines
Worked out from ESPN kickoff times (ET): one hour before the first game of each day. Sunday + Monday games are due
together at noon Sunday, or earlier if a Sunday game (e.g. London) kicks off before 1 PM. Once a deadline passes the
server refuses changes to those games. Override any day in **Admin → Week → Pick deadlines**.

## Running locally
```sh
npm install && pip install -r backend/requirements.txt
python3 -m backend.manage create-user <you> --admin   # first time only
npm start                                              # API on :8000, site on :5173
```
The first user created gets the picks from the pre-accounts database (it is migrated automatically on first start;
the original is kept as `backend/data/pool.pre-accounts.db`).

## Railway
1. Push this repo to GitHub (private is fine).
2. Railway → **New Project → Deploy from GitHub repo** → pick the repo. It builds from the `Dockerfile`.
3. In the service: **Settings → Volumes → Add volume**, mount path **`/data`** (the database lives there).
4. **Variables**: `ADMIN_USERNAME` and `ADMIN_PASSWORD`. Used only to create the first admin when the database
   has no users.
5. **Settings → Networking → Generate domain** to get a `*.up.railway.app` URL and check it works.
6. Bring your season over: run the app locally once, open **Admin → Backup → Download backup**, then on the live
   site **Admin → Backup → Restore** with that file. Log in again afterwards.

## Custom domain
1. Buy the domain (Cloudflare Registrar, Porkbun or Namecheap; roughly $10–15/year).
2. Railway → service → **Settings → Networking → Custom domain** → enter e.g. `picks.yourdomain.com`.
3. Add the DNS record Railway shows (a `CNAME`, plus a `TXT` verification record if asked) at your registrar.
   On Cloudflare, set the record to **DNS only** (grey cloud) until Railway shows the domain as verified.
4. Railway issues the HTTPS certificate automatically, usually within minutes.

## Backups
Admin → Backup → **Download backup** saves everything (accounts, lines, picks, images) as one `.db` file. Do it
every week or so. Railway volumes also have snapshot backups in the volume settings.
