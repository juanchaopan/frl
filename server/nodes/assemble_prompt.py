from state import ConversationState


def assemble_prompt(state: ConversationState) -> ConversationState:
    system_content = (
        "You are a French learning assistant. "
        "Your goal is to help the user memorize French vocabulary, phrases, and sentence expressions.\n\n"
        "## How you interact\n"
        "- Primarily ask Chinese → French translation questions (CHN→FRE), occasionally French → Chinese (FRE→CHN).\n"
        "- Draw questions from the user's vocabulary list and from any content in the conversation "
        "(e.g. words or phrases extracted from image descriptions).\n"
        "- Invent related translation problems that reinforce and extend what the user already knows.\n"
        "- After the user answers, immediately tell them whether they are correct or not, "
        "provide the correct answer with a brief explanation if needed, then ask the next question.\n"
        "- Keep a encouraging, patient tone. One question at a time.\n\n"
        "## User's vocabulary (long-term memory)\n"
    )
    if state.get("long_term_memory"):
        system_content += state["long_term_memory"]
    else:
        system_content += "(empty — no vocabulary recorded yet)"

    messages = [{"role": "system", "content": system_content}]

    for m in state.get("message_history", []):
        messages.append({"role": m["role"], "content": m["content"]})

    request = state["request"]
    user_content = request["content"]
    for url, description in zip(request["image_urls"], request["image_descriptions"]):
        user_content += f"\n\n## Image ({url})\n{description}"

    messages.append({"role": "user", "content": user_content})

    return {**state, "prompt": messages}
