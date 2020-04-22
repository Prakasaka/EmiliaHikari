from io import BytesIO
from time import sleep
from typing import Optional

from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler
from telegram.ext.dispatcher import run_async

import emilia.modules.sql.users_sql as sql
from emilia import dispatcher, OWNER_ID, LOGGER
from emilia.modules.helper_funcs.filters import CustomFilters

import emilia.modules.sql.feds_sql as fedsql
from emilia.modules.helper_funcs.alternate import send_message

USERS_GROUP = 4


def get_user_id(username):
    # ensure valid userid
    if len(username) <= 5:
        return None

    if username.startswith('@'):
        username = username[1:]

    users = sql.get_userid_by_name(username)

    if not users:
        return None

    elif len(users) == 1:
        return users[0].user_id

    else:
        for user_obj in users:
            try:
                userdat = dispatcher.bot.get_chat(user_obj.user_id)
                if userdat.username == username:
                    return userdat.id

            except BadRequest as excp:
                if excp.message == 'Chat not found':
                    pass
                else:
                    LOGGER.exception("Error extracting user ID")

    return None


@run_async
def broadcast(update, context):
    to_send = update.effective_message.text.split(None, 1)
    if len(to_send) >= 2:
        chats = sql.get_all_chats() or []
        failed = 0
        for chat in chats:
            try:
                context.bot.sendMessage(int(chat.chat_id), to_send[1])
                sleep(0.1)
            except TelegramError:
                failed += 1
                LOGGER.warning("Couldn't send broadcast to %s, group name %s", str(chat.chat_id), str(chat.chat_name))

        send_message(update.effective_message, "Broadcast complete. {} group failed to receive message, maybe because it was kicked".format(failed))


def slist(update, context):
    message = update.effective_message
    for user_id in OWNER_ID:
        try:
            owner = context.bot.get_chat(user_id)
            name = "[{}](tg://user?id={})".format(owner.first_name + (owner.last_name or ""), owner.id)
            if owner.username:
                name = escape_markdown("@" + owner.username)
            text = "👑 Bot Owner:\n`{}`".format(name)
        except BadRequest as excp:
            if excp.message == 'Chat not found':
                text += "\n - ({}) - not found".format(user_id)
    for user_id in SUDO_USERS:
        try:
            user = context.bot.get_chat(user_id)
            name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
            if user.username:
                name = escape_markdown("@" + user.username)
            text1 += "\n\nSudo Users:\n`{}`".format(name)
        except BadRequest as excp:
            if excp.message == 'Chat not found':
                text1 += "\n - ({}) - not found".format(user_id)
    send_message(update.effective_message, text + "\n" + text1 + "\n", parse_mode=ParseMode.MARKDOWN)


@run_async
def log_user(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    """text = msg.text if msg.text else ""
                uid = msg.from_user.id
                uname = msg.from_user.name
                print("{} | {} | {} | {}".format(text, uname, uid, chat.title))"""
    fed_id = fedsql.get_fed_id(chat.id)
    if fed_id:
        user = update.effective_user
        if user:
            fban, fbanreason, fbantime = fedsql.get_fban_user(fed_id, user.id)
            if fban:
                send_message(update.effective_message, "This user is banned in the current federation!\nReason: `{}`".format(fbanreason), parse_mode="markdown")
                try:
                    context.bot.kick_chat_member(chat.id, user.id)
                except:
                	print("Fban: cannot banned this user")

    sql.update_user(msg.from_user.id,
                    msg.from_user.username,
                    chat.id,
                    chat.title)

    if msg.reply_to_message:
        sql.update_user(msg.reply_to_message.from_user.id,
                        msg.reply_to_message.from_user.username,
                        chat.id,
                        chat.title)

    if msg.forward_from:
        sql.update_user(msg.forward_from.id,
                        msg.forward_from.username)

@run_async
def chats(update, context):
    all_chats = sql.get_all_chats() or []
    chatfile = 'Chat list.\n'
    for chat in all_chats:
        chatfile += "{} - ({})\n".format(chat.chat_name, chat.chat_id)

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "chatlist.txt"
        update.effective_message.reply_document(document=output, filename="chatlist.txt",
                                                caption="The following is a list of chats in my database.")


def __user_info__(user_id, chat_id):
    if user_id == dispatcher.bot.id:
        return "I've seen them in... Wow. Are they stalking me? They're in all the same places I am... oh. It's me."
    num_chats = sql.get_user_num_chats(user_id)
    return "I've seen them in <code>{}</code> chats in total.".format(num_chats)


def __stats__():
    return "{} users, across {} chats".format(sql.num_users(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""  # no help string

__mod_name__ = "Users"

BROADCAST_HANDLER = CommandHandler("broadcast", broadcast, filters=Filters.user(OWNER_ID))
SLIST_HANDLER = CommandHandler("slist", slist, filters=Filters.user(OWNER_ID))
USER_HANDLER = MessageHandler(Filters.all & Filters.group, log_user)
CHATLIST_HANDLER = CommandHandler("chatlist", chats, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(SLIST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
