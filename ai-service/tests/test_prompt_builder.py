"""Unit tests for the prompt builder."""

import pytest

from app.domain.entities import ConversationMessage
from app.domain.prompt_builder import build_first_message_prompt, build_reply_prompt

def test_first_message_prompt_structure():
    msgs = build_first_message_prompt("Bar El Sol", "Sos un vendedor de páginas web.")

    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"

def test_first_message_prompt_contains_commerce_name():
    msgs = build_first_message_prompt("Café Luna", "Sos un vendedor.")

    system_content = msgs[0]["content"]
    assert "Café Luna" in system_content

def test_first_message_prompt_contains_system_prompt():
    custom_prompt = "Mi prompt personalizado de ventas."
    msgs = build_first_message_prompt("Bar X", custom_prompt)

    assert custom_prompt in msgs[0]["content"]

def test_reply_prompt_structure_with_history():
    conversation = [
        ConversationMessage(role="assistant", content="Hola! Te contacto para..."),
        ConversationMessage(role="user", content="Sí, me interesa más info."),
    ]
    msgs = build_reply_prompt("Resto YYY", "Sos un vendedor.", conversation)

    roles = [m["role"] for m in msgs]
    assert roles[0] == "system"
    assert roles[1] == "assistant"
    assert roles[2] == "user"

def test_reply_prompt_last_message_is_from_user():
    """The last message in the list must be the customer's so the model replies."""
    conversation = [
        ConversationMessage(role="assistant", content="Primer mensaje."),
        ConversationMessage(role="user", content="¿Cuánto cuesta?"),
    ]
    msgs = build_reply_prompt("Bar", "Prompt.", conversation)

    assert msgs[-1]["role"] == "user"

def test_reply_prompt_contains_commerce_name():
    conversation = [ConversationMessage(role="user", content="Hola")]
    msgs = build_reply_prompt("Parrilla Don Roberto", "Prompt.", conversation)

    assert "Parrilla Don Roberto" in msgs[0]["content"]

def test_format_rules_in_both_prompts():
    """Format rules should be injected into both prompt types."""
    first = build_first_message_prompt("Bar", "Prompt.")
    reply = build_reply_prompt(
        "Bar", "Prompt.", [ConversationMessage(role="user", content="Hola")]
    )

    assert "máximo 3 oraciones" in first[0]["content"]
    assert "máximo 3 oraciones" in reply[0]["content"]
