from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown

import emilia.modules.sql.rules_sql as sql
from emilia import dispatcher, OWNER_ID
from emilia.modules.helper_funcs.chat_status import user_admin
from emilia.modules.helper_funcs.misc import build_keyboard_alternate
from emilia.modules.helper_funcs.string_handling import markdown_parser, button_markdown_parser
from emilia.modules.connection import connected

from emilia.modules.helper_funcs.alternate import send_message


@run_async
def get_rules(update, context):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# Do not async - not from a handler
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user  # type: Optional[User]
    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message == "Chat not found" and from_pm:
            bot.send_message(user.id, "The rules shortcut for this chat hasn't been set properly! Ask admins to fix this.")
            return
        else:
            raise

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title

    rules, buttons = button_markdown_parser(sql.get_rules(chat_id))
    try:
        text = "The rules for *{}* are:\n\n{}".format(escape_markdown(chat.title), rules)
    except TypeError:
        send_message(update.effective_message, "You can do this command in groups, not PM")
        return ""

    is_private = sql.get_private_rules(chat_id)

    if from_pm and rules:
        bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(build_keyboard_alternate(buttons)))
    elif from_pm:
        if conn:
            bot.send_message(user.id, "The group admins haven't set any rules for *{}*. This probably doesn't mean it's lawless though...!".format(chat_name), parse_mode="markdown")
        else:
            bot.send_message(user.id, "The group admins haven't set any rules for this chat yet. This probably doesn't mean it's lawless though...!")
    elif rules:
        if (update.effective_message.chat.type == "private" or not is_private) and rules:
            if not is_private:
                send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(build_keyboard_alternate(buttons)))
            else:
                bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(build_keyboard_alternate(buttons)))
        else:
            send_message(update.effective_message, "Contact me in PM to get this group's rules.",
                                                reply_markup=InlineKeyboardMarkup(
                                                    [[InlineKeyboardButton(text="Rules",
                                                                           url="t.me/{}?start={}".format(bot.username,
                                                                                                         chat_id))]]))
    else:
        if conn:
            send_message(update.effective_message, "The group admins haven't set any rules for *{}*. This probably doesn't mean it's lawless though...!".format(chat_name), parse_mode="markdown")
        else:
            send_message(update.effective_message, "The group admins haven't set any rules for this chat yet. This probably doesn't mean it's lawless though...!")


@run_async
@user_admin
def set_rules(update, context):
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    user = update.effective_user
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, "You can do this command in groups, not PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)

        sql.set_rules(chat_id, markdown_rules)
        if conn:
            send_message(update.effective_message, "Successfully set rules for *{}*.".format(chat_name), parse_mode="markdown")
        else:
            send_message(update.effective_message, "Successfully set rules for this group.")

    elif msg.reply_to_message and len(args) == 1:
        txt = msg.reply_to_message.text
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)

        sql.set_rules(chat_id, markdown_rules)
        if conn:
            send_message(update.effective_message, "Successfully set rules for *{}*.".format(chat_name), parse_mode="markdown")
        else:
            send_message(update.effective_message, "Successfully set rules for this group.")


@run_async
@user_admin
def clear_rules(update, context):
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    user = update.effective_user

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, "You can do this command in groups, not PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    chat_id = update.effective_chat.id
    sql.set_rules(chat_id, "")
    send_message(update.effective_message, "Successfully cleared rules!")


@run_async
@user_admin
def private_rules(update, context):
    args = context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(context.bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = chat.title
        else:
            chat_name = chat.title

    if len(args) >= 1:
        if args[0] in ("yes", "on", "ya"):
            sql.private_rules(str(chat_id), True)
            send_message(update.effective_message, "Private Rules was *enabled*, rules message will send to PM.", parse_mode="markdown")
        elif args[0] in ("no", "off"):
            sql.private_rules(str(chat_id), False)
            send_message(update.effective_message, "Private Rules was *disabled*, rules message will send to group.", parse_mode="markdown")
        else:
            send_message(update.effective_message, "Unknown argument - please use 'yes', or 'no'.")
    else:
        is_private = sql.get_private_rules(chat_id)
        send_message(update.effective_message, "Private Rules Settings in {}: *{}*".format(chat_name, "Enabled" if is_private else "Disabled"), parse_mode="markdown")


def __stats__():
    return OWNER_ID, "{} chats have rules set.".format(sql.num_chats())


def __import_data__(chat_id, data):
    # set chat rules
    rules = data.get('info', {}).get('rules', "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return user_id, "This chat has had it's rules set: `{}`".format(bool(sql.get_rules(chat_id)))


__help__ = """
 - /rules: get the rules for this chat.

*Admin only:*
 - /setrules <your rules here>: set the rules for this chat.
 - /clearrules: clear the rules for this chat.
 - /privaterules <yes/no/on/off>: should the rules be sent to private chat. Default: yes.
"""

__mod_name__ = "Rules"

GET_RULES_HANDLER = CommandHandler("rules", get_rules)#, filters=Filters.group)
SET_RULES_HANDLER = CommandHandler("setrules", set_rules)#, filters=Filters.group)
RESET_RULES_HANDLER = CommandHandler("clearrules", clear_rules)#, filters=Filters.group)
PRIVATERULES_HANDLER = CommandHandler("privaterules", private_rules, pass_args=True)

dispatcher.add_handler(GET_RULES_HANDLER)
dispatcher.add_handler(SET_RULES_HANDLER)
dispatcher.add_handler(RESET_RULES_HANDLER)
dispatcher.add_handler(PRIVATERULES_HANDLER)
