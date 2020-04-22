import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html, escape_markdown

from emilia import CUSTOM_CMD, dispatcher, CustomCommandHandler
from emilia.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict, bot_can_delete
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.log_channel import loggable
from emilia.modules.sql import cleaner_sql as sql
from emilia.modules.connection import connected

from emilia.modules.helper_funcs.alternate import send_message


if CUSTOM_CMD:
    CMD_STARTERS = ('/', '!')
else:
    CMD_STARTERS = ('/')

BLUE_TEXT_CLEAN_GROUP = 15


CommandHandlerList = (CommandHandler, CustomCommandHandler, DisableAbleCommandHandler)
command_list = ["cleanbluetext", "ignorecleanbluetext", "unignorecleanbluetext", "listcleanbluetext", "ignoreglobalcleanbluetext", "unignoreglobalcleanbluetext"
                "start", "help", "settings"]

for handler_list in dispatcher.handlers:
    for handler in dispatcher.handlers[handler_list]:
        if any(isinstance(handler, cmd_handler) for cmd_handler in CommandHandlerList):
            command_list += handler.command

@run_async
def clean_blue_text_must_click(update, context):
        chat = update.effective_chat
        message = update.effective_message

        if chat.get_member(context.bot.id).can_delete_messages:
                if sql.is_enabled(chat.id):
                        fst_word = message.text.strip().split(None, 1)[0]

                        if len(fst_word) > 1 and any(fst_word.startswith(start) for start in CMD_STARTERS):

                                command = fst_word[1:].split('@')
                                chat = update.effective_chat

                                ignored = sql.is_command_ignored(chat.id, command[0])
                                if ignored:
                                        return

                                if command[0] not in command_list:
                                        message.delete()

@run_async
@user_admin
def set_blue_text_must_click(update, context):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user  # type: Optional[User]
        message = update.effective_message  # type: Optional[Message]
        args = context.args

        conn = connected(context.bot, update, chat, user.id, need_admin=True)
        if conn:
                chat_id = conn
                chat_name = dispatcher.bot.getChat(conn).title
        else:
                if update.effective_message.chat.type == "private":
                        send_message(update.effective_message, "You can do this command in groups, not PM")
                        return ""
                chat_id = update.effective_chat.id
                message = update.effective_message
                chat_name = update.effective_message.chat.title

        if len(args) >= 1:
                val = args[0].lower()
                if val == "off" or val == "no":
                        sql.set_cleanbt(chat_id, False)
                        if conn:
                                text = "Blue text cleaner was *disabled* in *{}*.".format(chat_name)
                        else:
                                text = "Blue text cleaner was *disabled*."
                        send_message(update.effective_message, text, parse_mode="markdown")

                elif val == "yes" or val == "ya" or val == "on":
                        sql.set_cleanbt(chat_id, True)
                        if conn:
                                text = "Blue text cleaner was *enabled* in *{}*.".format(chat_name)
                        else:
                                text = "Blue text cleaner was *enabled*."
                        send_message(update.effective_message, text, parse_mode="markdown")

                else:
                        send_message(update.effective_message, "Unknown argument - please use 'yes', or 'no'.")
        else:
                send_message(update.effective_message, "Curent settings for Blue text cleaner at {}: *{}*".format(chat_name, "Enabled" if sql.is_enable(chat_id) else "Disabled"), parse_mode="markdown")

@run_async
@user_admin
def add_bluetext_ignore(update, context):
        message = update.effective_message
        args = context.args
        chat = update.effective_chat

        if len(args) >= 1:
                val = args[0].lower()
                added = sql.chat_ignore_command(chat.id, val)
                if added:
                        reply = "<b>{}</b> has been added to bluetext cleaner ignore list.".format(args[0])
                else:
                        reply = "Command is already ignored."
                send_message(update.effective_message, reply, parse_mode=ParseMode.HTML)
        
        else:
                reply = "No command supplied to be ignored."
                send_message(update.effective_message, reply)

@run_async
@user_admin
def remove_bluetext_ignore(update, context):

    message = update.effective_message
    args = context.args
    chat = update.effective_chat

    if len(args) >= 1:
        val = args[0].lower()
        removed = sql.chat_unignore_command(chat.id, val)
        if removed:
            reply = "<b>{}</b> has been removed from bluetext cleaner ignore list.".format(args[0])
        else:
            reply = "Command isn't ignored currently."
        send_message(update.effective_message, reply, parse_mode=ParseMode.HTML)
        
    else:
        reply = "No command supplied to be unignored."
        send_message(update.effective_message, reply)


@run_async
@user_admin
def add_bluetext_ignore_global(update, context):

    message = update.effective_message
    args = context.args

    if len(args) >= 1:
        val = args[0].lower()
        added = sql.global_ignore_command(val)
        if added:
            reply = "<b>{}</b> has been added to global bluetext cleaner ignore list.".format(args[0])
        else:
            reply = "Command is already ignored."
        send_message(update.effective_message, reply, parse_mode=ParseMode.HTML)
        
    else:
        reply = "No command supplied to be ignored."
        send_message(update.effective_message, reply)


@run_async
def remove_bluetext_ignore_global(update, context):

    message = update.effective_message
    args = context.args

    if len(args) >= 1:
        val = args[0].lower()
        removed = sql.global_unignore_command(val)
        if removed:
            reply = "<b>{}</b> has been removed from global bluetext cleaner ignore list.".format(args[0])
        else:
            reply = "Command isn't ignored currently."
        send_message(update.effective_message, reply, parse_mode=ParseMode.HTML)
        
    else:
        reply = "No command supplied to be unignored."
        send_message(update.effective_message, reply)


@run_async
def bluetext_ignore_list(bot: Bot, update: Update):

    message = update.effective_message
    chat = update.effective_chat

    global_ignored_list, local_ignore_list = sql.get_all_ignored(chat.id)
    text = ""

    if global_ignored_list:
        text = "The following commands are currently ignored globally from bluetext cleaning :\n"

        for x in global_ignored_list:
            text += f" - <code>{x}</code>\n"

    if local_ignore_list:
        text += "\nThe following commands are currently ignored locally from bluetext cleaning :\n"

        for x in local_ignore_list:
            text += f" - <code>{x}</code>\n"

    if text == "":
        text = "No commands are currently ignored from bluetext cleaning."
        send_message(update.effective_message, text)
        return

    send_message(update.effective_message, text, parse_mode=ParseMode.HTML)
    return

__help__ = """
 - /cleanbluetext <on/off/yes/no> - clean commands after sending
 - /ignorecleanbluetext <word> - prevent auto cleaning of the command
 - /unignorecleanbluetext <word> - remove prevent auto cleaning of the command
 - /listcleanbluetext - list currently whitelisted commands
"""

__mod_name__ = "Cleaner"

SET_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("cleanbluetext", set_blue_text_must_click, pass_args=True)
ADD_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("ignorecleanbluetext", add_bluetext_ignore, pass_args=True)
REMOVE_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("unignorecleanbluetext", remove_bluetext_ignore, pass_args=True)
ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER = CommandHandler("ignoreglobalcleanbluetext", add_bluetext_ignore_global, pass_args=True)
REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER = CommandHandler("unignoreglobalcleanbluetext", remove_bluetext_ignore_global, pass_args=True)
LIST_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("listcleanbluetext", bluetext_ignore_list)
CLEAN_BLUE_TEXT_HANDLER = MessageHandler(Filters.command & Filters.group, clean_blue_text_must_click)

dispatcher.add_handler(SET_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(ADD_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(REMOVE_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER)
dispatcher.add_handler(REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER)
dispatcher.add_handler(LIST_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(CLEAN_BLUE_TEXT_HANDLER, BLUE_TEXT_CLEAN_GROUP)
