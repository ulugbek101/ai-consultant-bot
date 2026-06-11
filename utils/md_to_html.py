import re


def md_to_html(text: str) -> str:
    """Convert LLM markdown output to Telegram-compatible HTML."""
    # Escape HTML entities before any substitution
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Fenced code blocks  ```lang\n...\n```
    text = re.sub(
        r"```(?:[a-zA-Z0-9]*)\n?(.*?)```",
        lambda m: f"<pre>{m.group(1).rstrip()}</pre>",
        text, flags=re.DOTALL,
    )

    # Inline code `code`
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)

    # Bold **text** and __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text, flags=re.DOTALL)

    # Italic *text* (single asterisk, not already-processed bold)
    text = re.sub(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    # Italic _text_ (not adjacent to a word character)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<i>\1</i>", text)

    # Strikethrough ~~text~~
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    # Headers # through ###### → bold line
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # Horizontal rules --- / *** / ___
    text = re.sub(r"^[-*_]{3,}\s*$", "—————", text, flags=re.MULTILINE)

    # Unordered bullets  - item  or  * item
    text = re.sub(r"^[ \t]*[-*•]\s+", "• ", text, flags=re.MULTILINE)

    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
