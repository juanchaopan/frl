from state import ConversationState


def assemble_prompt(state: ConversationState) -> ConversationState:
    history = state.get("message_history", [])
    has_prior_question = any(m["role"] == "assistant" for m in history)

    validate_step = (
        "1. Validate the user's translation:\n"
        "   - If correct: prefix with ✅ and show what they wrote.\n"
        "   - If wrong: prefix with ❌ and show what they wrote, then on a new line ✅ and the correct answer.\n"
    ) if has_prior_question else ""

    next_step = "2." if has_prior_question else "1."

    system_content = (
        "You are a French learning assistant. "
        "Your role is to quiz the user on French vocabulary, phrases, and sentence expressions.\n\n"
        "## How you respond\n"
        + validate_step +
        f"{next_step} Pick the next item to quiz using this priority:\n"
        "   a. Any item from the conversation history that was answered incorrectly — retest it.\n"
        "   b. Any item from the conversation history not yet tested.\n"
        "   c. Only when ALL items from the conversation history have been tested and answered correctly, "
        "draw a new item from the vocabulary list.\n"
        f"{'3' if has_prior_question else '2'}. Output the chosen item as a single word, phrase, or sentence expression "
        "in Chinese or French for the user to translate. Alternate CHN→FRE and FRE→CHN.\n"
        f"{'4' if has_prior_question else '3'}. No extra commentary, greetings, or explanations. "
        "Output only the check result and the next item.\n\n"
        "## User's vocabulary (long-term memory)\n"
    )
    if state.get("long_term_memory"):
        system_content += state["long_term_memory"]
    else:
        system_content += "(empty — no vocabulary recorded yet)"

    messages = [{"role": "system", "content": system_content}]

    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})

    request = state["request"]
    user_content = request["content"]
    for key, description in zip(request["image_keys"], request["image_descriptions"]):
        user_content += f"\n\n## Image ({key})\n{description}"

    messages.append({"role": "user", "content": user_content})

    return {"prompt": messages}
