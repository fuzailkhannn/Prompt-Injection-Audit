"""Order-management agent. The model can look up, cancel, and refund orders via tools."""
from fastapi import FastAPI, Depends
from openai import OpenAI
import json

from .auth import get_current_user          # returns the authenticated User
from .orders import get_order, cancel_order, issue_refund

app = FastAPI()
client = OpenAI()

TOOLS = [
    {"type": "function", "function": {
        "name": "cancel_order",
        "description": "Cancel an order by id.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "issue_refund",
        "description": "Refund an order by id.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string"}, "amount": {"type": "number"}}},
    }},
]


def run_tool(name: str, args: dict):
    # Execute whatever the model asked for.
    if name == "cancel_order":
        return cancel_order(args["order_id"])
    if name == "issue_refund":
        return issue_refund(args["order_id"], args["amount"])
    return {"error": "unknown tool"}


@app.post("/agent/orders")
def orders_agent(message: str, user=Depends(get_current_user)):
    messages = [
        {"role": "system", "content": "You help the customer manage their orders."},
        {"role": "user", "content": message},
    ]
    completion = client.chat.completions.create(
        model="gpt-4o", messages=messages, tools=TOOLS,
    )
    choice = completion.choices[0].message
    results = []
    for call in (choice.tool_calls or []):
        args = json.loads(call.function.arguments)
        results.append(run_tool(call.function.name, args))
    return {"results": results}
