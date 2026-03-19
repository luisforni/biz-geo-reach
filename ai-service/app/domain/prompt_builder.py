"""Prompt construction utilities.

Pattern: Builder — assembles the Ollama messages array from domain objects
so that API handlers and the service layer stay free of prompt logic.

All prompt instructions are in Spanish (rioplatense) to match the target
audience (Argentine bars and restaurants).
"""

from app.domain.entities import ConversationMessage

_FORMAT_RULES = (
    "Reglas de formato para WhatsApp:\n"
    "- Mensajes cortos: máximo 3 oraciones.\n"
    "- Sin asteriscos ni markdown.\n"
    "- Sin listas con viñetas.\n"
    "- Tono amigable y rioplatense (usá 'vos', 'te', 'tu').\n"
    "- No reveles que sos una IA a menos que te lo pregunten directamente.\n"
    "- No uses más de 1 emoji por mensaje."
)

def build_first_message_prompt(
    commerce_name: str,
    system_prompt: str,
) -> list[dict[str, str]]:
    """Build the Ollama messages array for a first-contact message.

    Args:
        commerce_name: Name of the target bar/restaurant.
        system_prompt: Sales persona defined by the campaign operator.

    Returns:
        List of ``{"role": str, "content": str}`` dicts ready for Ollama /api/chat.
    """
    combined_system = (
        f"{system_prompt}\n\n"
        f"{_FORMAT_RULES}\n\n"
        f'El nombre del comercio que vas a contactar es: "{commerce_name}".'
    )

    user_instruction = (
        "Escribí el primer mensaje de WhatsApp para este comercio.\n"
        "Debe despertar interés, ser breve y terminar con una pregunta "
        "que invite a responder."
    )

    return [
        {"role": "system", "content": combined_system},
        {"role": "user", "content": user_instruction},
    ]

def build_reply_prompt(
    commerce_name: str,
    system_prompt: str,
    conversation: list[ConversationMessage],
) -> list[dict[str, str]]:
    """Build the Ollama messages array to continue an ongoing conversation.

    Replays the full conversation history so the model has context,
    then appends an instruction to generate the next assistant turn.

    Args:
        commerce_name: Name of the commerce (for system context).
        system_prompt: Sales persona defined by the campaign operator.
        conversation: Existing message history from campaign-service.

    Returns:
        List of ``{"role": str, "content": str}`` dicts ready for Ollama /api/chat.
    """
    combined_system = (
        f"{system_prompt}\n\n"
        f"{_FORMAT_RULES}\n\n"
        f'El comercio con el que estás conversando se llama: "{commerce_name}".\n'
        "Si el cliente muestra interés en continuar, intentá coordinar una llamada. "
        "Si rechaza definitivamente, despedite amablemente y no insistas."
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": combined_system}
    ]

    for msg in conversation:
        messages.append({"role": msg.role, "content": msg.content})

    return messages
