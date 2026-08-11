# citadel/commands/games.py
"""Games menu -- a purely informational listing (same style as
KnownRoomsCommand). Games themselves are normal top-level commands
(e.g. Trivia's "T"), usable directly whether or not you've sent this
first."""

from citadel.commands.base import BaseCommand, CommandCategory
from citadel.commands.registry import register_command
from citadel.auth.permissions import PermissionLevel
from citadel.transport.packets import ToUser


@register_command
class GamesCommand(BaseCommand):
    code = "P"
    name = "games"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Play games"
    help_text = "List available games."

    async def run(self, context):
        return ToUser(
            session_id=context.session_id,
            text="Games:\nT - Trivia\nX - Tic-Tac-Toe\n\nSend the letter to play."
        )
