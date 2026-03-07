# 🔒 Incognish (ABANDONNED Data-brokers make it too hard to automate deletion request)

A self-hosted, personal data-broker opt-out tracker.
Automates removal requests to 49 data brokers and tracks every request status over time.

> **For personal use.** Your data never leaves your machine.

---

## Features

- **49 data brokers** catalogued with opt-out methods and URLs
- **Automated submissions** via headless browser (Playwright) for 12 brokers
- **CAPTCHA solving** via [CapSolver](https://capsolver.com) for Turnstile-protected brokers (optional)
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

## Automation Coverage

### Fully Automated (Playwright)

These brokers run without any manual steps. Turnstile-protected ones require a CapSolver API key.

| Broker | CAPTCHA | Notes |
|--------|---------|-------|
| TruePeopleSearch | — | Headless browser |
| FastPeopleSearch | — | Headless browser |
| FamilyTreeNow | — | Headless browser |
| BeenVerified | Turnstile ¹ | Email verification to finalize |
| PeopleFinders | Turnstile ¹ | Email confirmation to finalize |
| Intelius | Turnstile ¹ | PeopleConnect suppression center — also covers ZabaSearch, TruthFinder, InstantCheckmate |
| ZabaSearch | Turnstile ¹ | Same as Intelius |
| ClustrMaps | Turnstile ¹ | Email confirmation to finalize |
| VoterRecords | Cloudflare ² | Falls back to manual if blocked |
| PublicRecordsNow | Cloudflare ² | Falls back to manual if blocked |
| Smart Background Checks | Cloudflare ² | Falls back to manual if blocked |
| ThatsThem | reCAPTCHA v2 ¹ | Falls back to manual if blocked |

¹ Requires `CAPSOLVER_API_KEY` in `.env`
² Cloudflare Enterprise — automation may be blocked depending on IP

### Email Automated (SMTP)

Requires `SMTP_*` credentials in `.env`.

| Broker | Contact |
|--------|---------|
| CheckPeople | support@checkpeople.com |
| Ancestry | privacy@ancestry.com |

### Manual (35 brokers)

The app shows you the exact opt-out URL and tracks when you complete it.

Spokeo, WhitePages, Radaris, MyLife, SearchPeopleFree, NumLookup, Acxiom, Epsilon,
TruthFinder, Instant Checkmate, Pipl, LexisNexis, Oracle Advertising (BlueKai),
Verecor, Addresses.com, US Phone Book, 411.com, Nuwber, Advanced Background Checks,
PeopleSearchNow, Cyber Background Checks, ZoomInfo, InfoTracer, USA People Search,
Veripages, PeekYou, SearchQuarry, Social Catfish, SpyFly, NeighborReport,
PeopleByName, PublicDataUSA, USA-Official, Rehold, UnMask

---

## Optional: CAPTCHA Solving (CapSolver)

Some brokers (BeenVerified, PeopleFinders, Intelius, ZabaSearch, ClustrMaps, ThatsThem) require solving a Cloudflare Turnstile or reCAPTCHA challenge. Incognish integrates with [CapSolver](https://capsolver.com) to handle this automatically.

**Cost:** ~$0.80–1.00 per 1,000 solves. A full opt-out run uses ~5 solves — under $0.01/run. Minimum deposit is $5 (~1,250 runs).

```bash
cp .env.example .env
# Add your key:
# CAPSOLVER_API_KEY=your_key_here
```

Without a key, Turnstile-protected brokers fall back to `manual_required`.

---

## Optional: Email Opt-Outs

Some brokers accept a GDPR/CCPA removal request by email. To automate these:

```bash
cp .env.example .env
# Fill in your SMTP credentials
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

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
- No analytics, no telemetry, no external calls except to broker websites (and CapSolver if configured)

---

## Project Structure

```
incognish/
├── brokers/
│   ├── registry.json          # 49 broker definitions
│   └── handlers/              # automation scripts per broker
│       ├── base.py            # BaseHandler + shared stealth browser helpers
│       ├── capsolver_helper.py # Turnstile / reCAPTCHA solving via CapSolver
│       ├── email_handler.py   # SMTP email opt-outs
│       └── <broker>.py        # one file per automated broker
├── core/
│   ├── tracker.py             # SQLite DB operations
│   └── engine.py              # opt-out orchestration
├── app/
│   ├── routes/                # Flask blueprints
│   ├── templates/             # Jinja2 HTML
│   └── static/                # CSS
├── .env.example               # copy to .env and fill in credentials
├── run.py                     # entry point
└── requirements.txt
```

---

## License

MIT — do whatever you want with it.
