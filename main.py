"""Astrbot plugin: auto-reply when mentioned or quoted."""
from astrbot import event
from astrbot.core import AstrbotConfig
from typing import Optional
import re


class AutoReplyMentionOrQuote:
    """Reply automatically when the bot is mentioned or quoted."""

    def __init__(self, config: AstrbotConfig):
        self.config = config
        self.reply_text: str = config.get("reply_text", "收到！")
        self.enabled: bool = config.get("enabled", True)

    @event.on_bot_mention_or_quote()
    async def on_mention_or_quote(self, event_obj, **kwargs):
        """Handle mention or quote events."""
        if not self.enabled:
            return

        raw_message = kwargs.get("raw_message", "")
        user_id = kwargs.get("user_id", "unknown")

        await event_obj.reply(self.reply_text)


def new_instance(config: AstrbotConfig):
    return AutoReplyMentionOrQuote(config)
