""" local mute (per chat), cat-style: deletes messages even from admins """

from pyrogram.errors.exceptions.forbidden_403 import MessageDeleteForbidden

from kannax import Config, Message, filters, get_collection, kannax
from kannax.utils.tools import is_dev

MUTE_BASE = get_collection("MUTE_USER")
CHANNEL = kannax.getCLogger(__name__)
LOG = kannax.getLogger(__name__)


@kannax.on_cmd(
    "mute",
    about={
        "header": "Mute a user in this chat",
        "description": "Messages from the muted user are deleted, "
        "even if they are admin (uses delete, not restrict).",
        "examples": "{tr}mute [userid | reply] [reason]",
    },
    allow_channels=False,
    allow_bots=False,
)
async def mute_user(msg: Message):
    """mute a user in this chat"""
    await msg.edit("`Muting this user...`")
    user_id, reason = msg.extract_user_and_text
    if not user_id:
        await msg.edit("`Reply to a user or give userid/username.`", del_in=5)
        return
    get_mem = await msg.client.get_user_dict(user_id)
    firstname = get_mem["fname"]
    user_id = get_mem["id"]
    if user_id == msg.from_user.id:
        await msg.err("You can't mute yourself.")
        return
    if is_dev(user_id) or user_id in Config.SUDO_USERS:
        await msg.err("Can't mute this user (dev/sudo).")
        return
    found = await MUTE_BASE.find_one({"user_id": user_id, "chat_id": msg.chat.id})
    if found:
        await msg.edit("`This user is already muted in this chat.`", del_in=5)
        return
    await MUTE_BASE.insert_one(
        {"firstname": firstname, "user_id": user_id, "chat_id": msg.chat.id,
         "reason": reason or ""}
    )
    await msg.edit(
        f"**#Muted** [{firstname}](tg://user?id={user_id}) in this chat."
        + (f"\n**Reason:** `{reason}`" if reason else "")
    )
    LOG.info("Muted %s in %s", str(user_id), str(msg.chat.id))


@kannax.on_cmd(
    "unmute",
    about={
        "header": "Unmute a user in this chat",
        "examples": "{tr}unmute [userid | reply]",
    },
    allow_channels=False,
    allow_bots=False,
)
async def unmute_user(msg: Message):
    """unmute a user in this chat"""
    await msg.edit("`Unmuting...`")
    user_id, _ = msg.extract_user_and_text
    if not user_id:
        await msg.edit("`Reply to a user or give userid/username.`", del_in=5)
        return
    get_mem = await msg.client.get_user_dict(user_id)
    firstname = get_mem["fname"]
    user_id = get_mem["id"]
    found = await MUTE_BASE.find_one({"user_id": user_id, "chat_id": msg.chat.id})
    if not found:
        await msg.edit("`This user is not muted in this chat.`", del_in=5)
        return
    await MUTE_BASE.delete_one({"user_id": user_id, "chat_id": msg.chat.id})
    await msg.edit(f"**#Unmuted** [{firstname}](tg://user?id={user_id}) in this chat.")
    LOG.info("Unmuted %s in %s", str(user_id), str(msg.chat.id))


@kannax.on_cmd(
    "mutelist",
    about={
        "header": "List users muted in this chat",
        "examples": "{tr}mutelist",
    },
    allow_channels=False,
)
async def list_muted(msg: Message):
    """list muted users in this chat"""
    users = ""
    async for c in MUTE_BASE.find({"chat_id": msg.chat.id}):
        users += f"**User:** {c['firstname']}\n**ID:** `{c['user_id']}`"
        if c.get("reason"):
            users += f"\n**Reason:** `{c['reason']}`"
        users += "\n\n"
    await msg.edit_or_send_as_file(
        f"**--Muted Users in this Chat--**\n\n{users}" if users else "`Nobody muted here.`"
    )


@kannax.on_filters(
    filters.group & filters.incoming & ~filters.edited,
    group=2,
    check_restrict_perm=True,
)
async def mute_watcher(msg: Message):
    """delete messages from locally muted users (even admins)"""
    if not msg.from_user:
        return
    muted = await MUTE_BASE.find_one({"user_id": msg.from_user.id, "chat_id": msg.chat.id})
    if muted:
        try:
            await msg.delete()
        except MessageDeleteForbidden:
            pass
        except Exception as e:
            LOG.info("mute watcher: %s", str(e))
