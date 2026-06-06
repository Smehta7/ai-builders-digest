# AI Builders Weekly Digest

Sends a rich HTML email digest every **Saturday at 10:56 AM IST** using:
- [`follow-builders`](https://github.com/zarazhangrui/follow-builders) central feed for content
- Anthropic API (`claude-sonnet`) for remixing
- Gmail SMTP for delivery
- GitHub Actions for scheduling (fully cloud, no local server)

---

## Repo structure to add

```
your-repo/
├── .github/
│   └── workflows/
│       └── ai-digest.yml       ← GH Actions workflow
└── digest/
    └── run_digest.py           ← Python: remix + render + send
```

---

## Setup (one-time, ~10 minutes)

### 1. Add files to your repo

Copy `.github/workflows/ai-digest.yml` and `digest/run_digest.py` into your repo and push.

### 2. Get a Gmail App Password

> Regular Gmail password won't work — Google requires an App Password for SMTP.

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** if not already on
3. Search for **"App Passwords"** → create one → name it "AI Digest"
4. Copy the 16-character password (shown once)

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (from [console.anthropic.com](https://console.anthropic.com)) |
| `GMAIL_USER` | Your Gmail address e.g. `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | The 16-char App Password from step 2 |
| `DIGEST_TO_EMAIL` | Where to send the digest (can be same Gmail) |

### 4. Test it manually

After pushing, go to your repo → **Actions → AI Builders Weekly Digest → Run workflow**.

You should receive an email within ~2 minutes.

---

## Schedule

Runs automatically every **Saturday at 10:56 AM IST** (05:26 UTC).

To change the schedule, edit the `cron` line in `.github/workflows/ai-digest.yml`:
```yaml
- cron: "26 5 * * 6"   # min hour day month weekday (6=Saturday, UTC)
```

Use [crontab.guru](https://crontab.guru) to build a different expression.

---

## Customizing the digest

The remixing prompt is in `digest/run_digest.py` — look for `SYSTEM_PROMPT` and `REMIX_SCHEMA`.

- **Tone**: Edit `SYSTEM_PROMPT` — currently set to "direct, analytical, occasional dry wit"
- **Focus areas**: The prompt already flags Databricks/data engineering relevance
- **Length**: Adjust `builders[:30]` cap in `remix_content()` for more/fewer builders
- **Language**: Add a translation instruction to `SYSTEM_PROMPT` for bilingual output

---

## Cost estimate

| Component | Cost |
|---|---|
| Anthropic API (claude-sonnet, ~4K tokens/week) | ~$0.02/week |
| GitHub Actions (well within free tier) | $0 |
| Gmail SMTP | $0 |

**~$1/year total.**
