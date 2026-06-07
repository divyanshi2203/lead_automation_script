"""
Lead automation backend.

A small FastAPI service that:
  - accepts leads (POST /lead)
  - classifies a message as Hot / Warm / Cold and drafts a reply (POST /classify)
  - returns every stored lead (GET /leads)
  - marks a lead as contacted (POST /leads/{lead_id}/contacted)

Storage is a plain JSON file so it is easy to read and inspect.
Classification uses Claude if an ANTHROPIC_API_KEY is set, otherwise it
falls back to a simple keyword rule so the project still runs with no key.
"""

import csv
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- file locations -------------------------------------------------------
HERE = Path(__file__).parent
DB_FILE = HERE / "leads.json"          # where leads are saved
SAMPLE_CSV = HERE / "sample_leads.csv"  # 10 test leads loaded on first run


# --- request body shapes (FastAPI validates incoming JSON against these) --
class Lead(BaseModel):
    name: str
    email: str
    phone: str
    message: str
    source: str


class Message(BaseModel):
    message: str


# --- tiny JSON "database" --------------------------------------------------
def read_leads():
    """Return the list of leads from the JSON file (empty list if none)."""
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text())
    return []


def write_leads(leads):
    """Save the whole list of leads back to the JSON file."""
    DB_FILE.write_text(json.dumps(leads, indent=2))


# --- the LLM part ----------------------------------------------------------
def classify_with_claude(message):
    """
    Ask Claude to classify the message and draft a reply.
    Returns a dict like {"classification": "Hot", "suggested_reply": "..."}.
    Raises an exception if the API key is missing or the call fails;
    the caller handles that and falls back to the rule below.
    """
    import anthropic  # imported here so the app still starts without the package

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    prompt = (
        "You triage sales leads. Read the message and respond with ONLY a JSON "
        'object: {"classification": "Hot|Warm|Cold", "suggested_reply": "<1-2 '
        'friendly sentences>"}. Hot = clear intent/budget/deadline. Warm = '
        "curious but vague. Cold = spam, unsubscribe, or no real interest.\n\n"
        f"Message: {message}"
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    data = json.loads(response.content[0].text)
    return {
        "classification": data["classification"],
        "suggested_reply": data["suggested_reply"],
    }


def classify_with_rules(message):
    """Keyword fallback used when Claude is unavailable. Keeps the app runnable."""
    text = message.lower()
    spam_words = ["unsubscribe", "click here", "win iphone", "shadydeal"]
    hot_words = ["budget", "call this week", "by end of month", "rfp", "engagement", "pay"]
    warm_words = ["free or paid", "brochure", "exploring", "know more", "pricing"]

    if any(word in text for word in spam_words) or len(text.strip()) < 6:
        label = "Cold"
    elif any(word in text for word in hot_words):
        label = "Hot"
    elif any(word in text for word in warm_words):
        label = "Warm"
    else:
        label = "Warm"

    replies = {
        "Hot": "Thanks for reaching out — this sounds like a great fit. When are you free for a quick call this week?",
        "Warm": "Thanks for your message! Happy to share more details — could you tell me a bit about what you're looking for?",
        "Cold": "Thanks for getting in touch. Let us know if there's anything specific we can help with.",
    }
    return {"classification": label, "suggested_reply": replies[label]}


def classify(message):
    """Try Claude first, fall back to rules on any error (basic error handling)."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return classify_with_claude(message)
        except Exception as error:
            print(f"[classify] Claude call failed, using rules instead: {error}")
    return classify_with_rules(message)


# --- the API ---------------------------------------------------------------
app = FastAPI(title="Lead Automation")

# Allow the Next.js frontend (different port) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def save_lead(lead_dict):
    """Classify a lead, give it an id + status, store it, and return it."""
    result = classify(lead_dict["message"])
    leads = read_leads()
    lead_dict["id"] = len(leads) + 1
    lead_dict["classification"] = result["classification"]
    lead_dict["suggested_reply"] = result["suggested_reply"]
    lead_dict["status"] = "New"
    leads.append(lead_dict)
    write_leads(leads)
    return lead_dict


@app.on_event("startup")
def seed_from_csv():
    """On first run, load the 10 sample leads so the dashboard isn't empty."""
    if read_leads():
        return
    if not SAMPLE_CSV.exists():
        return
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            save_lead(dict(row))
    print("Seeded sample leads.")


@app.post("/lead")
def create_lead(lead: Lead):
    """Accept a new lead, classify it, store it, and return the stored record."""
    return save_lead(lead.model_dump())


@app.get("/leads")
def get_leads():
    """Return every stored lead with its classification and suggested reply."""
    return read_leads()


@app.post("/classify")
def classify_message(payload: Message):
    """Classify a raw message string without storing anything."""
    return classify(payload.message)


@app.post("/leads/{lead_id}/contacted")
def mark_contacted(lead_id: int):
    """Set a lead's status to 'Contacted'."""
    leads = read_leads()
    for lead in leads:
        if lead["id"] == lead_id:
            lead["status"] = "Contacted"
            write_leads(leads)
            return lead
    raise HTTPException(status_code=404, detail="Lead not found")
