"""
AI Builders Weekly Digest
--------------------------
1. Reads raw JSON from /tmp/raw-digest.json (output of prepare-digest.js)
2. Calls Anthropic API to remix content into a structured digest
3. Renders a rich HTML email
4. Sends via Gmail SMTP
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic

RAW_JSON_PATH = "/tmp/raw-digest.json"
TODAY = datetime.now().strftime("%B %d, %Y")
WEEK_LABEL = datetime.now().strftime("Week of %B %d")


# ── 1. Load raw content ──────────────────────────────────────────────────────

def load_raw(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    builders = data.get("x", [])
    podcasts = data.get("podcasts", [])
    prompts  = data.get("prompts", {})
    stats    = data.get("stats", {})
    if not builders and not podcasts:
        print("No content today — skipping.")
        sys.exit(0)
    print(f"Loaded {len(builders)} builders | {len(podcasts)} podcast(s)")
    return {"builders": builders, "podcasts": podcasts, "prompts": prompts, "stats": stats}


# ── 2. Remix via Anthropic API ───────────────────────────────────────────────

SYSTEM_PROMPT = """You are a sharp, opinionated AI research editor who curates a weekly digest for a 
senior data engineer and Databricks architect. Your reader is technical, busy, and values 
original builder thinking over hype. Tone: direct, analytical, occasionally dry wit.

Rules:
- Summarize each builder's posts into 2-3 punchy sentences. Lead with the insight, not the person.
- For podcasts: extract 3-5 key takeaways as tight bullet points.
- Never fabricate. Only use content from the JSON.
- Every summary MUST include the source URL exactly as provided.
- Flag anything relevant to: AI agents, data engineering, LLMs, infra, Databricks, or the modern data stack.
- Output ONLY valid JSON — no preamble, no markdown fences."""

REMIX_SCHEMA = """
Return this exact JSON structure:
{
  "headline": "one punchy sentence summarizing the week's biggest theme",
  "builders": [
    {
      "name": "...",
      "role": "...",  // infer from bio field
      "summary": "...",  // 2-3 sentences
      "url": "...",  // most relevant tweet URL
      "data_relevance": true/false  // true if relevant to data/AI infra
    }
  ],
  "podcasts": [
    {
      "show": "...",
      "episode": "...",
      "takeaways": ["...", "...", "..."],
      "url": "..."
    }
  ],
  "editors_pick": "name of one builder whose insight was most worth reading this week",
  "editors_note": "one sentence on why"
}
"""

def remix_content(raw: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Trim content to avoid token overflow — cap at 30 builders
    builders = raw["builders"][:30]
    podcasts = raw["podcasts"][:2]

    user_content = f"""
Here is this week's raw content from the AI builders feed.

BUILDERS (X/Twitter posts):
{json.dumps(builders, indent=2)}

PODCASTS:
{json.dumps(podcasts, indent=2)}

Today's date: {TODAY}

{REMIX_SCHEMA}
"""

    print("Calling Anthropic API for remix...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}]
    )

    raw_text = response.content[0].text.strip()
    # Strip markdown fences if model included them anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        raw_text = raw_text.rsplit("```", 1)[0]

    digest = json.loads(raw_text)
    print(f"Remix complete — {len(digest.get('builders', []))} builders, {len(digest.get('podcasts', []))} podcasts")
    return digest


# ── 3. Render HTML email ─────────────────────────────────────────────────────

def render_html(digest: dict) -> str:
    builders_html = ""
    for b in digest.get("builders", []):
        badge = (
            '<span style="background:#1a1a2e;color:#64ffda;font-size:10px;'
            'font-weight:700;padding:2px 7px;border-radius:3px;letter-spacing:0.05em;'
            'text-transform:uppercase;margin-left:8px;">Data/AI Infra</span>'
            if b.get("data_relevance") else ""
        )
        builders_html += f"""
        <div style="border-left:3px solid #64ffda;padding:14px 0 14px 20px;margin-bottom:24px;">
          <div style="font-size:13px;font-weight:700;color:#64ffda;letter-spacing:0.08em;
                      text-transform:uppercase;margin-bottom:4px;">
            {b.get('name','')}
            <span style="color:#8892a4;font-weight:400;text-transform:none;letter-spacing:0;">
              · {b.get('role','')}
            </span>
            {badge}
          </div>
          <p style="margin:6px 0 10px;color:#ccd6f6;line-height:1.65;font-size:15px;">
            {b.get('summary','')}
          </p>
          <a href="{b.get('url','')}" style="color:#64ffda;font-size:12px;
             text-decoration:none;letter-spacing:0.03em;">→ View post</a>
        </div>"""

    podcasts_html = ""
    for p in digest.get("podcasts", []):
        takeaways = "".join(
            f'<li style="margin-bottom:6px;color:#ccd6f6;">{t}</li>'
            for t in p.get("takeaways", [])
        )
        podcasts_html += f"""
        <div style="background:#0d1b2a;border-radius:8px;padding:20px 24px;margin-bottom:20px;">
          <div style="font-size:12px;color:#64ffda;font-weight:700;letter-spacing:0.1em;
                      text-transform:uppercase;margin-bottom:4px;">{p.get('show','')}</div>
          <div style="font-size:16px;font-weight:600;color:#e6f1ff;margin-bottom:12px;">
            {p.get('episode','')}
          </div>
          <ul style="margin:0;padding-left:18px;font-size:14px;line-height:1.7;">
            {takeaways}
          </ul>
          <a href="{p.get('url','')}" style="display:inline-block;margin-top:12px;
             color:#64ffda;font-size:12px;text-decoration:none;">→ Listen</a>
        </div>"""

    editors_pick = digest.get("editors_pick", "")
    editors_note = digest.get("editors_note", "")
    headline     = digest.get("headline", "This week in AI building")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Builders Digest — {TODAY}</title>
</head>
<body style="margin:0;padding:0;background:#0a0f1e;font-family:'Georgia',serif;">

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="background:linear-gradient(135deg,#0a0f1e 0%,#0d1b2a 100%);
                 padding:40px 0 0;text-align:center;">
        <div style="font-family:'Courier New',monospace;font-size:11px;letter-spacing:0.25em;
                    color:#64ffda;text-transform:uppercase;margin-bottom:12px;">
          Follow Builders, Not Influencers
        </div>
        <h1 style="margin:0;font-family:'Georgia',serif;font-size:28px;font-weight:400;
                   color:#e6f1ff;letter-spacing:-0.02em;">
          AI Builders Digest
        </h1>
        <div style="font-size:13px;color:#8892a4;margin-top:8px;font-family:monospace;">
          {WEEK_LABEL} · {TODAY}
        </div>
        <!-- Divider -->
        <div style="margin:28px auto 0;width:60px;height:2px;
                    background:linear-gradient(90deg,transparent,#64ffda,transparent);"></div>
      </td>
    </tr>
  </table>

  <!-- Main content -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="padding:0 20px;">
        <div style="max-width:640px;margin:0 auto;">

          <!-- Headline -->
          <div style="margin:36px 0 32px;padding:24px 28px;
                      background:#0d1b2a;border-radius:10px;
                      border:1px solid rgba(100,255,218,0.15);">
            <div style="font-family:monospace;font-size:10px;color:#64ffda;
                        letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px;">
              This week's theme
            </div>
            <p style="margin:0;font-size:18px;color:#e6f1ff;line-height:1.5;
                      font-style:italic;font-weight:400;">
              "{headline}"
            </p>
          </div>

          <!-- Editor's Pick -->
          <div style="margin-bottom:32px;padding:18px 22px;
                      background:rgba(100,255,218,0.05);
                      border:1px solid rgba(100,255,218,0.2);border-radius:8px;">
            <div style="font-family:monospace;font-size:10px;color:#64ffda;
                        letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">
              ★ Editor's Pick
            </div>
            <span style="color:#e6f1ff;font-weight:600;">{editors_pick}</span>
            <span style="color:#8892a4;font-size:14px;"> — {editors_note}</span>
          </div>

          <!-- Builders Section -->
          <h2 style="font-family:monospace;font-size:11px;letter-spacing:0.2em;
                     color:#8892a4;text-transform:uppercase;font-weight:400;
                     border-bottom:1px solid #1a2640;padding-bottom:10px;margin-bottom:24px;">
            Builders on X
          </h2>
          {builders_html}

          <!-- Podcasts Section -->
          {"<h2 style='font-family:monospace;font-size:11px;letter-spacing:0.2em;color:#8892a4;text-transform:uppercase;font-weight:400;border-bottom:1px solid #1a2640;padding-bottom:10px;margin:36px 0 20px;'>Podcast Highlights</h2>" + podcasts_html if podcasts_html else ""}

        </div>
      </td>
    </tr>
  </table>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="padding:40px 20px;text-align:center;">
        <div style="font-family:monospace;font-size:11px;color:#3d4f6b;letter-spacing:0.05em;">
          Powered by follow-builders · Delivered every Saturday · 
          <a href="https://github.com/zarazhangrui/follow-builders"
             style="color:#3d4f6b;text-decoration:underline;">source</a>
        </div>
      </td>
    </tr>
  </table>

</body>
</html>"""


# ── 4. Send via Gmail SMTP ───────────────────────────────────────────────────

def send_email(html_body: str):
    gmail_user     = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    to_email       = os.environ["DIGEST_TO_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🧠 AI Builders Digest — {TODAY}"
    msg["From"]    = f"AI Builders Digest <{gmail_user}>"
    msg["To"]      = to_email

    msg.attach(MIMEText(html_body, "html"))

    print(f"Sending digest to {to_email}...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())
    print("Email sent successfully.")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    raw    = load_raw(RAW_JSON_PATH)
    digest = remix_content(raw)
    html   = render_html(digest)
    send_email(html)
