# citadel/transport/engines/meshcore/bot_channel.py
"""Listens on a configured MeshCore channel (e.g. "#bot") and replies to
simple triggers. v1 is deliberately minimal: ping -> pong, proving the
whole path (channel config on the radio, receiving CHANNEL_MSG_RECV,
replying via send_chan_msg) before anything needing per-message logic
gets built on top of it.

Channel messages carry no sender-identity field at the protocol level
(unlike direct messages) -- just channel_idx, text, and a timestamp --
so triggers here are necessarily channel-wide, not per-user.
"""

import logging

from meshcore import EventType

log = logging.getLogger(__name__)


class BotChannelHandler:
    def __init__(self, meshcore, config):
        self.meshcore = meshcore
        self.bot_config = config.transport.get("meshcore", {}).get("bot_channel", {})
        self.channel_index = None

    async def start(self):
        if not self.meshcore:
            log.warning("BotChannelHandler: no MeshCore connection, skipping")
            return

        if not self.bot_config.get("enabled", False):
            log.info("Bot channel disabled in config")
            return

        index = self.bot_config.get("index")
        name = self.bot_config.get("name", "#bot")
        if index is None:
            log.error("BotChannelHandler: no channel index configured, skipping")
            return

        existing = await self.meshcore.commands.get_channel(index)
        if existing.type != EventType.ERROR:
            existing_name = existing.payload.get("channel_name", "")
            if existing_name and existing_name != name:
                log.warning(
                    f"Bot channel: slot {index} currently holds '{existing_name}', "
                    f"overwriting with '{name}'"
                )

        result = await self.meshcore.commands.set_channel(index, name)
        if result.type == EventType.ERROR:
            log.error(f"Bot channel: failed to configure '{name}' at slot {index}: {result.payload}")
            return

        self.channel_index = index
        log.info(f"Bot channel '{name}' configured at slot {index}")

    async def handle_channel_message(self, event):
        data = event.payload or {}
        log.debug(f"Bot channel: received event, configured_index={self.channel_index}, payload={data}")

        if self.channel_index is None:
            return

        if data.get("channel_idx") != self.channel_index:
            return

        text = (data.get("text") or "").strip()
        # The MeshCore app prefixes channel messages with the sender's
        # display name ("Name: message"), since channel messages have no
        # separate sender-identity field at the protocol level. Strip it
        # before matching triggers.
        if ": " in text:
            _, _, text = text.partition(": ")
        text = text.strip().lower()

        if text == "ping":
            reply = self._pong_reply(data)
            await self.meshcore.commands.send_chan_msg(self.channel_index, reply)

    @staticmethod
    def _pong_reply(data) -> str:
        """Signal-quality diagnostics, not just an ack -- SNR and hop
        count are the closest LoRa equivalent to what round-trip time
        tells you on a normal ping. No node name: that's already visible
        in the MeshCore app's UI, so it'd just be redundant here."""
        details = []

        snr = data.get("SNR")
        if snr is not None:
            details.append(f"SNR {snr}")

        path_len = data.get("path_len")
        if isinstance(path_len, int) and path_len >= 0:
            hop_word = "hop" if path_len == 1 else "hops"
            details.append(f"{path_len} {hop_word}")

        return f"pong ({', '.join(details)})" if details else "pong"
