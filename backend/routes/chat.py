"""AI chat endpoint — Claude Haiku streaming recommendations."""

import json
import os

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from auth import get_current_user
from database import actresses_collection, user_actresses_collection
from drama_metadata import DRAMA_META
from helpers import _oid, _merge_user_data, _ensure_user_list

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

router = APIRouter(prefix="/api")


def _build_system_prompt(user_id: str | None) -> str:
    query = {}
    if user_id:
        _ensure_user_list(user_id)
        user_actress_ids = [
            _oid(d["actressId"]) for d in user_actresses_collection.find({"userId": user_id}, {"actressId": 1})
        ]
        query["_id"] = {"$in": user_actress_ids}
    docs = list(actresses_collection.find(query))
    for d in docs:
        d["_id"] = str(d["_id"])
    _merge_user_data(docs, user_id)

    lines = ["You are a K-Drama recommendation assistant. You know every K-Drama ever made.",
             "The user has a tier-ranked list of K-Drama actresses and their dramas.",
             "Use this data to give personalized recommendations.",
             "Be enthusiastic but concise. Use drama titles in quotes.",
             "If asked about something unrelated to K-Dramas, politely steer back.",
             "", "=== USER'S ACTRESS RANKINGS & DRAMAS ==="]
    for doc in docs:
        tier = doc.get("tier") or "Unranked"
        name = doc["name"]
        genre = doc.get("genre", "")
        lines.append(f"\n{name} (Tier: {tier}, Genre: {genre})")
        for d in doc.get("dramas", []):
            rating = d.get("rating")
            watch = d.get("watchStatus")
            meta = DRAMA_META.get(d["title"], {})
            parts = [f'  - "{d["title"]}" ({d.get("year", "?")})']
            if d.get("role"):
                parts.append(f'role: {d["role"]}')
            if rating:
                parts.append(f"rating: {rating}/10")
            if watch:
                parts.append(f"status: {watch}")
            if meta.get("genre"):
                parts.append(f"genre: {meta['genre']}")
            lines.append(", ".join(parts))
    return "\n".join(lines)


@router.post("/chat")
async def chat(request: Request, user=Depends(get_current_user)):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI chat is not configured")

    body = await request.json()
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Messages are required")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system_prompt = _build_system_prompt(user["uid"] if user else None)

    def generate():
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
