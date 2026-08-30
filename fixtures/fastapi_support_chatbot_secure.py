"""Support chatbot endpoint — scoped version. Answers a customer's own account questions."""
import json
import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI

from .auth import get_current_user      # verifies session token -> User
from .db import get_session             # ordinary per-request app DB session

app = FastAPI()
client = OpenAI()
log = logging.getLogger("support")

SYSTEM_PROMPT = """You are Acme's support assistant. Answer the customer's questions
about their account. Respond as JSON: {"answer": "..."}."""


@app.post("/support/chat")
def support_chat(message: str, user=Depends(get_current_user), db: Session = Depends(get_session)):
    log.info("support_chat", extra={"user_id": user.id})

    # Scope every read to the authenticated user. No id comes from the request.
    customer = db.query(Customer).filter(Customer.id == user.id).one()
    context = {"plan": customer.plan, "balance": customer.balance}

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"Account: {json.dumps(context)}"},
                {"role": "user", "content": message},
            ],
        )
        parsed = json.loads(completion.choices[0].message.content)
    except Exception:
        log.exception("support_chat failed")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    # Return only the whitelisted field, never the raw completion.
    return {"answer": str(parsed.get("answer", ""))}
