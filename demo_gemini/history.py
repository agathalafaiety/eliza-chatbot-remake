"""Validate and synchronize Gemini conversations stored in the visitor's browser."""

from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

import streamlit as st
from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_MESSAGE_LENGTH = 1000
MAX_REPLY_LENGTH = 8000
MAX_CONVERSATIONS = 20
MAX_TURNS = 30


class Turn(BaseModel):
    model_config = ConfigDict(strict=True, hide_input_in_errors=True)

    user: Annotated[str, Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)]
    assistant: Annotated[str, Field(min_length=1, max_length=MAX_REPLY_LENGTH)]


class Conversation(BaseModel):
    model_config = ConfigDict(strict=True, hide_input_in_errors=True)

    id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    turns: list[Turn] = Field(min_length=1, max_length=MAX_TURNS)

    @property
    def title(self) -> str:
        text = " ".join(self.turns[0].user.split())
        return text if len(text) <= 60 else f"{text[:59]}…"


class BrowserSnapshot(BaseModel):
    history: list[Conversation] = Field(default_factory=list, max_length=MAX_CONVERSATIONS)
    command_id: str | None = Field(default=None, alias="commandId")
    error: Literal["conflict", "full", "write"] | None = None
    unavailable: bool = False


_bridge = st.components.v2.component(
    "eliza_gemini_browser_history",
    js=Path(__file__).with_name("browser_history.js").read_text(encoding="utf-8"),
)


def browser_snapshot(command: dict | None) -> BrowserSnapshot | None:
    """Read the visitor's snapshot only after the browser has loaded it."""
    result = _bridge(
        data={"command": command}, key="eliza_history", on_snapshot_change=lambda: None
    )
    if result.snapshot is None:
        return None
    try:
        if len(result.snapshot) <= 760_000:
            snapshot = BrowserSnapshot.model_validate_json(result.snapshot)
            if len({item.id for item in snapshot.history}) == len(snapshot.history):
                return snapshot
    except (TypeError, ValidationError):
        pass
    return BrowserSnapshot(unavailable=True)


def save_turn(conversation: Conversation | None, message: str, reply: str) -> dict:
    turns = conversation.turns if conversation else []
    updated = Conversation(
        id=conversation.id if conversation else uuid4().hex,
        turns=[*turns, Turn(user=message, assistant=reply[:MAX_REPLY_LENGTH])],
    )
    return {
        "id": uuid4().hex,
        "operation": "save",
        "conversationId": updated.id,
        "previousTurns": len(turns),
        "conversation": updated.model_dump(),
    }


def delete_conversation(conversation_id: str) -> dict:
    return {"id": uuid4().hex, "operation": "delete", "conversationId": conversation_id}
