import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from emilia import dispatcher, LOGGER
from emilia.modules.helper_funcs.chat_status import user_admin, can_delete
from emilia.modules.log_channel import loggable

from emilia.modules.helper_funcs.alternate import send_message


@run_async
@user_admin
@loggable
def purge(update, context):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]
    if msg.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, context.bot.id):
            message_id = msg.reply_to_message.message_id
            if args and args[0].isdigit():
                if int(args[0]) < int(1):
                    return
                delete_to = message_id + int(args[0])
            else:
                delete_to = msg.message_id - 1
            for m_id in range(delete_to, message_id - 1, -1):  # Reverse iteration over message ids
                try:
                    context.bot.deleteMessage(chat.id, m_id)
                except BadRequest as err:
                    if err.message == "Message can't be deleted":
                        send_message(update.effective_message, "Cannot delete all messages. The messages may be too old, I might not have delete rights, or this might not be a supergroup.")

                    elif err.message != "Message to delete not found":
                        LOGGER.exception("Error while purging chat messages.")

            try:
                msg.delete()
            except BadRequest as err:
                if err.message == "Message can't be deleted":
                    send_message(update.effective_message, "Cannot delete all messages. The messages may be too old, I might not have delete rights, or this might not be a supergroup.")

                elif err.message != "Message to delete not found":
                    LOGGER.exception("Error while purging chat messages.")

            a = send_message(update.effective_message, "Purge complete.")
            try:
                a.delete()
            except BadRequest:
                pass
            return "<b>{}:</b>" \
                   "\n#PURGE" \
                   "\n<b>Admin:</b> {}" \
                   "\nPurged <code>{}</code> messages.".format(html.escape(chat.title),
                                                               mention_html(user.id, user.first_name),
                                                               delete_to - message_id)

    else:
        send_message(update.effective_message, "Reply to a message to select where to start purging from.")

    return ""


@run_async
@user_admin
@loggable
def del_message(update, context) -> str:
    chat = update.effective_chat
    if update.effective_message.reply_to_message:
        user = update.effective_user
        if can_delete(chat, context.bot.id):
            update.effective_message.reply_to_message.delete()
            try:
                update.effective_message.delete()
            except BadRequest:
                pass
            return "<b>{}:</b>" \
                   "\n#DEL" \
                   "\n<b>• Admin:</b> {}" \
                   "\nMessage deleted.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))
    else:
        send_message(update.effective_message, "Whadya want to delete?")

    return ""


__help__ = """
*Admin only:*
 - /del: deletes the message you replied to
 - /purge: deletes all messages between this and the replied to message.
 - /purge <integer X>: deletes the replied message, and X messages following it.
"""

__mod_name__ = "Purges"

DELETE_HANDLER = CommandHandler("del", del_message, filters=Filters.group)
PURGE_HANDLER = CommandHandler("purge", purge, filters=Filters.group, pass_args=True)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)
