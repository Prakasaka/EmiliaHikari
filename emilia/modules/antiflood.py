import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async, CallbackQueryHandler
from telegram.utils.helpers import mention_html, escape_markdown

from emilia import dispatcher
from emilia.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.log_channel import loggable
from emilia.modules.sql import antiflood_sql as sql
from emilia.modules.connection import connected

from emilia.modules.helper_funcs.alternate import send_message

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(update, context) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            chat.kick_member(user.id)
            execstrings = "Get out!"
            tag = "BANNED"
        elif getmode == 2:
            chat.kick_member(user.id)
            chat.unban_member(user.id)
            execstrings = "Get out!"
            tag = "KICKED"
        elif getmode == 3:
            context.bot.restrict_chat_member(chat.id, user.id, permissions=ChatPermissions(can_send_messages=False))
            execstrings = "Now you shutup!"
            tag = "MUTED"
        elif getmode == 4:
            bantime = extract_time(msg, getvalue)
            chat.kick_member(user.id, until_date=bantime)
            execstrings = "Get out for {}!".format(getvalue)
            tag = "TBAN"
        elif getmode == 5:
            mutetime = extract_time(msg, getvalue)
            context.bot.restrict_chat_member(chat.id, user.id, until_date=mutetime, permissions=ChatPermissions(can_send_messages=False))
            execstrings = "Now you shutup for {}!".format(getvalue)
            tag = "TMUTE"
        send_message(update.effective_message, "I like to leave the flooding to natural disasters. But you, you were just a disappointment. {}".format(execstrings))

        return "<b>{}:</b>" \
               "\n#{}" \
               "\n<b>User:</b> {}" \
               "\nFlooded the group.".format(tag, html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        send_message(update.effective_message, "I can't kick people here, give me permissions first! Until then, I'll disable antiflood.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#INFO" \
               "\n{}".format(chat.title, "Don't have kick permissions, so automatically disabled antiflood.")


@run_async
@user_admin
@loggable
def set_flood(update, context) -> str:
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
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat_id, 0)
            if conn:
                text = "Antiflood has been disabled in *{}*.".format(chat_name)
            else:
                text ="Antiflood has been disabled."
            send_message(update.effective_message, text, parse_mode="markdown")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = "Antiflood has been disabled in *{}*.".format(chat_name)
                else:
                    text = "Antiflood has been disabled."
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nDisable antiflood.".format(html.escape(chat_name), mention_html(user.id, user.first_name))

            elif amount < 3:
                send_message(update.effective_message, "Antiflood has to be either 0 (disabled), or a number bigger than 3")
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = "Antiflood has been updated and set to *{}* in *{}*".format(amount, chat_name)
                else:
                    text = "Antiflood has been updated and set to *{}*".format(amount)
                send_message(update.effective_message, text, parse_mode="markdown")
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nSet antiflood to <code>{}</code>.".format(html.escape(chat_name),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            send_message(update.effective_message, "Unrecognised argument - please use a number, 'off', or 'no'.")
    else:
        send_message(update.effective_message, "Use `/setflood number` to set antiflood.\nOr use `/setflood off` for disable antiflood.", parse_mode="markdown")
    return ""


@run_async
def flood(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    conn = connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, "You can do this command in groups, not PM")
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        if conn:
            text = "I'm not currently enforcing flood control in *{}*!".format(chat_name)
        else:
            text = "I'm not currently enforcing flood control!"
        send_message(update.effective_message, text, parse_mode="markdown")
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = 'banned'
        elif getmode == 2:
            settypeflood = 'kicked'
        elif getmode == 3:
            settypeflood = 'muted'
        elif getmode == 4:
            settypeflood = 'temporarily banned for {}'.format(getvalue)
        elif getmode == 5:
            settypeflood = 'temporarily muted for {}'.format(getvalue)
        if conn:
            text = "This chat is currently enforcing flood control after *{}* messages. Any users sending more than that amount of messages will be *{}* in *{}*.".format(limit, settypeflood, chat_name)
#             text = "If member is flooding messages, they will got *{}* in *{}*.".format(settypeflood, chat_name)
        else:
            text = "This chat is currently enforcing flood control after *{}* messages. Any users sending more than that amount of messages will be *{}*.".format(limit, settypeflood)
#             text = "If member is flooding messages, they will got *{}*.".format(settypeflood)
        send_message(update.effective_message, text, parse_mode="markdown")
#     else:
#         if conn:
#             text = "I'm currently banning users if they send more than *{}* consecutive messages in *{}*.".format(limit, chat_name)
#         else:
#             text = "I'm currently banning users if they send more than *{}* consecutive messages.".format(limit)
#         send_message(update.effective_message, text, parse_mode="markdown")


@run_async
@user_admin
def set_flood_mode(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

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

    if args:
        if args[0].lower() == 'ban':
            settypeflood = 'banned'
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == 'kick':
            settypeflood = 'kicked'
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == 'mute':
            settypeflood = 'muted'
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == 'tban':
            if len(args) == 1:
                teks = """It looks like you are trying to set a temporary value for antiflood, but has not determined the time; use `/setfloodmode tban <timevalue>`.
                          Examples of time values: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 week."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "temp banned for {}".format(args[1])
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == 'tmute':
            if len(args) == 1:
                teks = """It looks like you are trying to set a temporary value for antiflood, but has not determined the time; use `/setfloodmode tban <timevalue>`.
                          Examples of time values: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 week."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "temp mute for {}".format(args[1])
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            send_message(update.effective_message, "I only understand ban/kick/mute/tban/tmute!")
            return
        if conn:
            text = "Flooding messages now will result `{}` in *{}*!".format(settypeflood, chat_name)
        else:
            text = "Flooding messages now will result `{}`!".format(settypeflood)
        send_message(update.effective_message, text, parse_mode="markdown")
        return "<b>{}:</b>\n" \
                "<b>Admin:</b> {}\n" \
                "Has changed antiflood mode. User will {}.".format(settypeflood, html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = 'banned'
        elif getmode == 2:
            settypeflood = 'kicked'
        elif getmode == 3:
            settypeflood = 'muted'
        elif getmode == 4:
            settypeflood = 'temp banned for {}'.format(getvalue)
        elif getmode == 5:
            settypeflood = 'temp mute for {}'.format(getvalue)
        if conn:
            text = "If member is flooding messages, they will got *{}* in *{}*.".format(settypeflood, chat_name)
        else:
            text = "If member is flooding messages, they will got *{}*.".format(settypeflood)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "*Not* currently enforcing flood control."
    else:
        return "Antiflood is set to `{}` messages.".format(limit)


"""
def __chat_settings_btn__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        status = "❎ Tidak Aktif"
    else:
        status = "✅ Aktif"
    button = []
    button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
            InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_wlim=?|{}".format(chat_id)),
            InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
    button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
    return button

def FLOOD_EDITBTN(update, context):
    query = update.callback_query
    user = update.effective_user
    print("User {} clicked button FLOOD EDIT".format(user.id))
    qdata = query.data.split("=")[1].split("|")[0]
    chat_id = query.data.split("|")[1]
    if qdata == "?":
        context.bot.answerCallbackQuery(query.id, "Batas dari pesan beruntun. Jika pengguna mengirim pesan lebih dari batas, maka akan langsung di banned.", show_alert=True)
    if qdata == "-":
        button = []
        limit = sql.get_flood_limit(chat_id)
        limit = int(limit)-1
        if limit == 0:
            status = "❎ Tidak Aktif"
        else:
            status = "✅ Aktif"
        if limit <= 2:
            context.bot.answerCallbackQuery(query.id, "Batas limit Tidak boleh kurang dari 3", show_alert=True)
            return
        sql.set_flood(chat_id, int(limit))
        chat = context.bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Anti Pesan Beruntun*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal pesan beruntun telah di setel menjadi `{}`.".format(limit)
        button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_flim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        context.bot.answer_callback_query(query.id)
    if qdata == "+":
        button = []
        limit = sql.get_flood_limit(chat_id)
        limit = int(limit)+1
        if limit == 0:
            status = "❎ Tidak Aktif"
        else:
            status = "✅ Aktif"
        if limit <= 0:
            context.bot.answerCallbackQuery(query.id, "Batas limit Tidak boleh kurang dari 0", show_alert=True)
            return
        sql.set_flood(chat_id, int(limit))
        chat = context.bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Anti Pesan Beruntun*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal pesan beruntun telah di setel menjadi `{}`.".format(limit)
        button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_flim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        context.bot.answer_callback_query(query.id)
    if qdata == "exec":
        button = []
        limit = sql.get_flood_limit(chat_id)
        if limit == 0:
            sql.set_flood(chat_id, 3)
            limit = 3
            status = "✅ Aktif ({})".format(limit)
        else:
            sql.set_flood(chat_id, 0)
            limit = 0
            status = "❎ Tidak Aktif"
        chat = context.bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Anti Pesan Beruntun*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal pesan beruntun telah di setel menjadi `{}`.".format(status)
        button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_flim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        context.bot.answer_callback_query(query.id)
"""


__help__ = """
 - /flood: Get the current flood control setting

*Admin only:*
 - /setflood <int/'no'/'off'>: enables or disables flood control
 - /setfloodmode <ban/kick/mute/tban/tmute> <value>: select the action perform when warnings have been exceeded. ban/kick/mute/tmute/tban

 Note:
 - Value must be filled for tban and tmute, Can be:
        `4m` = 4 minutes
        `4h` = 4 hours
        `2d` = 2 days
        `1w` = 1 week
"""

__mod_name__ = "Antiflood"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True)#, filters=Filters.group)
SET_FLOOD_MODE_HANDLER = CommandHandler("setfloodmode", set_flood_mode, pass_args=True)#, filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood)#, filters=Filters.group)
# FLOOD_BTNSET_HANDLER = CallbackQueryHandler(FLOOD_EDITBTN, pattern=r"set_flim")

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_MODE_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
# dispatcher.add_handler(FLOOD_BTNSET_HANDLER)
