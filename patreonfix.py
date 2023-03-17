from asyncio import sleep
from os import getenv
from typing import Dict, List, Final

from dotenv import load_dotenv
from disnake import (
    Intents,
    Activity,
    Status,
    AuditLogEntry,
    AuditLogAction,
    Role,
    Client,
)

load_dotenv()

intents = Intents.none()
intents.members = True
intents.moderation = True

client = Client(
    intents=intents,
    status=Status.dnd,
    activity=Activity(name=f"Patreons bot make mistakes.", type=4),
)

ROLE_UPDATE: Dict[int, List[Role]] = {}

PATREON_DISCORD_BOT_ID: Final[int] = int(getenv("PATREON_DISCORD_BOT_ID"))
PATREON_ROLE_ID: Final[int] = int(getenv("PATREON_ROLE_ID"))
SLEEP_DURATION: Final[int] = int(getenv("SLEEP_DURATION"))


async def wait_and_check(entry: AuditLogEntry) -> None:
    # Wait for all roles to be removed by the Patreon bot.
    await sleep(SLEEP_DURATION)

    targeted_member = (
        entry.guild.get_member(entry.target.id) # Get member obj from cache.
        or await entry.guild.fetch_member(entry.target.id) # Fetch new member obj if not in cache.
    )

    removed_roles = [role for role in ROLE_UPDATE[entry.target.id]]

    if PATREON_ROLE_ID in [role.id for role in removed_roles]:
        # Patreon is removing roles from someone it should be removing roles from.
        return
    
    for role in removed_roles:
        # Add roles back that patreon mistakenly removed.
        await targeted_member.add_roles(role, reason="Adding role back that Patreon removed.")
    
    del ROLE_UPDATE[entry.target.id]


@client.event
async def on_connect() -> None:
    print("Bot has connected to the Discord gateway")


@client.listen("on_audit_log_entry_create")
async def on_audit_log_entry_create(entry: AuditLogEntry) -> None:
    if (
        entry.user.id == PATREON_DISCORD_BOT_ID
        and entry.action == AuditLogAction.member_role_update
        and len(entry.changes.before.roles) == 1 # Role was removed rather than added.
    ):
        removed_role = entry.changes.before.roles[0]
        targeted_user = entry.target

        if ROLE_UPDATE.get(targeted_user.id, None) is None:
            # The Patreon bot hasn't removed any roles yet.
            ROLE_UPDATE[targeted_user.id] = [removed_role]
            return await wait_and_check(entry)

        # Store addtional roles that the Patreon bot removes.
        ROLE_UPDATE[targeted_user.id].append(removed_role)


client.run(getenv("DISCORD_BOT_TOKEN"))
