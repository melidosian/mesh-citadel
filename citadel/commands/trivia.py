# citadel/commands/trivia.py

from citadel.commands.base import BaseCommand, CommandCategory
from citadel.commands.registry import register_command
from citadel.auth.permissions import PermissionLevel
from citadel.workflows.base import WorkflowContext, WorkflowState


@register_command
class TriviaCommand(BaseCommand):
    code = "T"
    name = "trivia"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Daily trivia"
    help_text = "Play today's trivia question. One question per day, shared by everyone."
    hidden = True  # discovered via P (Games), not the main H menu

    async def run(self, context):
        from citadel.workflows.registry import get as get_workflow

        wf_state = WorkflowState(kind="trivia", step=1, data={})
        context.session_mgr.set_workflow(context.session_id, wf_state)
        wf_context = WorkflowContext(
            session_id=context.session_id,
            db=context.db,
            config=context.config,
            session_mgr=context.session_mgr,
            wf_state=wf_state
        )

        workflow = get_workflow("trivia")
        return await workflow.start(wf_context)
