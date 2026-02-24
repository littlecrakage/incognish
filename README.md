# 🔒 Incognish

A self-hosted, personal data-broker opt-out tracker.
Automates removal requests to 30+ data brokers and tracks every request status over time.

> **For personal use.** Your data never leaves your machine.

---

## Features

- **30+ data brokers** catalogued with opt-out methods and URLs
- **Automated submissions** via headless browser (Playwright) for supported brokers
- **Email opt-outs** via SMTP for email-based brokers (optional)
- **Request tracking** — full history of every submission
- **Point-in-time snapshots** — see what your status was on any past date
- **Clean web UI** — runs at `localhost:5000`

---

## Quickstart (Windows)

```batch
git clone https://github.com/yourname/incognish.git
cd incognish
setup.bat
venv\Scripts\activate
python run.py
```

## Quickstart (Linux / macOS)

```bash
git clone https://github.com/yourname/incognish.git
cd incognish
chmod +x setup.sh && ./setup.sh
source venv/bin/activate
python run.py
```

The app opens at **http://localhost:5000** automatically.

---

## First Run

1. Go to **My Profile** and fill in your details (stored locally only)
2. Go to **Run Scan** and select the brokers you want to target
3. Click **Start Selected** — watch the live log
4. Check **Requests** for full history
5. Use **Reports** → Take Snapshot to save a point-in-time record

---

## Optional: Email Opt-Outs

Some brokers require an email opt-out. To automate these:

```bash
cp .env.example .env
# Edit .env with your SMTP credentials
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

---

## Automation Coverage

| Method | Brokers | Notes |
|---|---|---|
| `web_form` (Playwright) | TruePeopleSearch, FastPeopleSearch, FamilyTreeNow | Headless browser |
| `email` (SMTP) | Truthfinder, InstantCheckmate, CheckPeople, + more | Requires `.env` |
| `manual` | All others | App logs URL + instructions, you submit manually |

Brokers with no handler are marked `manual_required` — the app shows you the exact URL and tracks when you do it.

---

## Adding a New Broker

1. Add an entry to `brokers/registry.json`
2. Optionally create `brokers/handlers/yourbroker.py` with a `Handler` class extending `BaseHandler`
3. Set `"handler": "yourbroker"` in the registry entry

PRs to improve the broker registry are welcome!

---

## Data Privacy

- All data lives in `db/tracker.db` (SQLite) on your machine
- `db/` is gitignored — never committed
- No analytics, no telemetry, no external calls except to broker websites

---

## Project Structure

```
incognish/
├── brokers/
│   ├── registry.json          # 30+ broker definitions
│   └── handlers/              # automation scripts per broker
├── core/
│   ├── tracker.py             # SQLite DB operations
│   └── engine.py              # opt-out orchestration
├── app/
│   ├── routes/                # Flask blueprints
│   ├── templates/             # Jinja2 HTML
│   └── static/                # CSS
├── run.py                     # entry point
└── requirements.txt
```

---

## License

MIT — do whatever you want with it.
