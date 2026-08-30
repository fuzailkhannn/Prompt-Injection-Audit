"""Document Q&A view. User asks a question about an uploaded document."""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from anthropic import Anthropic
from .models import Document

anthropic = Anthropic()

SYSTEM_PROMPT = "You answer questions about the provided document for the user."


@csrf_exempt
def ask_document(request):
    payload = json.loads(request.body)
    doc_id = payload["doc_id"]
    question = payload["question"]

    # Fetch the document the user wants to ask about.
    document = Document.objects.get(id=doc_id)

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Document title: {document.title}\n"
        f"Document body:\n{document.body}\n\n"
        f"Question: {question}"
    )

    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return JsonResponse({"answer": response.content[0].text})
