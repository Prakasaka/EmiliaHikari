import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode, ChatMember
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, MessageHandler, run_async, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html, mention_markdown

from emilia import dispatcher, LOGGER, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from emilia.modules.helper_funcs.chat_status import user_admin, user_not_admin, user_admin, is_user_ban_protected
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.log_channel import loggable
from emilia.modules.sql import reporting_sql as sql

from emilia.modules.helper_funcs.alternate import send_message

REPORT_GROUP = 5

CURRENT_REPORT = {}


@run_async
@loggable
@user_admin
def report_setting(update, context):
	chat = update.effective_chat  # type: Optional[Chat]
	msg = update.effective_message  # type: Optional[Message]
	args = context.args

	if chat.type == chat.PRIVATE:
		if len(args) >= 1:
			if args[0] in ("yes", "on"):
				sql.set_user_setting(chat.id, True)
				send_message(update.effective_message, "Turned on reporting! You'll be notified whenever anyone reports something.")

			elif args[0] in ("no", "off"):
				sql.set_user_setting(chat.id, False)
				send_message(update.effective_message, "Turned off reporting! You wont get any reports.")
		else:
			send_message(update.effective_message, "Your current report preference is: `{}`".format(sql.user_should_report(chat.id)),
						   parse_mode=ParseMode.MARKDOWN)

	else:
		if len(args) >= 1:
			if args[0] in ("yes", "on"):
				sql.set_chat_setting(chat.id, True)
				send_message(update.effective_message, "Turned on reporting! Admins who have turned on reports will be notified when /report or @admin are called.")

			elif args[0] in ("no", "off"):
				sql.set_chat_setting(chat.id, False)
				send_message(update.effective_message, "Turned off reporting! No admins will be notified on /report or @admin.")
		else:
			send_message(update.effective_message, "This chat's current setting is: `{}`".format(sql.chat_should_report(chat.id)),
						   parse_mode=ParseMode.MARKDOWN)
@run_async
@loggable
@user_admin
# @user_not_admin
def report(update, context) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args
    user_id = extract_user(message, args)

    if user_id == OWNER_ID:
        message.reply_text("are u reporting a bot owner? O bhai maaro mujhe maaro")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("OOOH someone's trying to report a sudo user! *grabs popcorn*")
        return

    if user_id == context.bot.id:
        message.reply_text("-_- So funny, lets report myself why don't I? Nice try.")
        return

    if is_user_ban_protected(chat, user_id):
        message.reply_text("dude. it is admin of this group")
        return

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user  # type: Optional[User]
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()

        if chat.username and chat.type == Chat.SUPERGROUP:
            msg = "<b>{}:</b>" \
                  "\n<b>Reported user:</b> {} (<code>{}</code>)" \
                  "\n<b>Reported by:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                                      mention_html(
                                                                          reported_user.id,
                                                                          reported_user.first_name),
                                                                      reported_user.id,
                                                                      mention_html(user.id,
                                                                                   user.first_name),
                                                                      user.id)
            # link = "\n<b>Link:</b> " \
            #        "<a href=\"http://telegram.me/{}/{}\">click here</a>".format(chat.username, message.message_id)
        else:
            msg = "{} is calling for admins in \"{}\"!".format(
                mention_html(user.id, user.first_name), html.escape(chat_name))
        if chat.username:
            chatlink = "https://t.me/{}/{}".format(chat.username, str(message.reply_to_message.message_id))
        else:
            chatlink = "https://t.me/c/{}/{}".format(str(chat.id)[4:], str(message.reply_to_message.message_id))
        # should_forward = False
        keyboard = [[InlineKeyboardButton(u"➡ Message", url=chatlink)],
                   [InlineKeyboardButton(u"⚠ Kick", callback_data="report_{}=kick={}={}".format(
                                    chat.id, reported_user.id,
                                    reported_user.first_name)),
                    InlineKeyboardButton(u"⛔️ Ban", callback_data="report_{}=banned={}={}".format(
                                    chat.id, reported_user.id,
                                    reported_user.first_name))],
                    [InlineKeyboardButton(u"❎ Delete Message", callback_data="report_{}=delete={}={}".format(
                                    chat.id, reported_user.id,
                                    message.reply_to_message.message_id))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        should_forward = True
        all_admins = []
        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue
            if sql.user_should_report(admin.user.id):
                all_admins.append("<a href='tg://user?id={}'>⁣</a>".format(admin.user.id))
                try:
                    try:
                        # context.bot.sendMessage(admin.user.id, msg, parse_mode=ParseMode.HTML)
                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)
                            if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)
                    except:
                        pass
                    context.bot.send_message(admin.user.id, msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
#                     if not chat.username:
#                         context.bot.sendMessage(admin.user.id, msg, parse_mode=ParseMode.HTML)

#                         if should_forward:
#                             message.reply_to_message.forward(admin.user.id)

#                             if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
#                                 message.forward(admin.user.id)

#                     if chat.username and chat.type == Chat.SUPERGROUP:
#                         context.bot.sendMessage(admin.user.id, msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

#                         if should_forward:
#                             message.reply_to_message.forward(admin.user.id)

#                             if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
#                                 message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("Exception while reporting user")
        context.bot.send_message(chat.id, "{} <b>has been reported to the admin</b>{}".format(
                    	mention_html(reported_user.id, reported_user.first_name),"".join(all_admins)),
                    	parse_mode="HTML", reply_to_message_id=message.reply_to_message.message_id)
        return msg
    return ""


def buttons(update, context):
    query = update.callback_query
    splitter = query.data.replace("report_", "").split("=")
    if splitter[1] == "kick":
        try:
            context.bot.kickChatMember(splitter[0], splitter[2])
            context.bot.unbanChatMember(splitter[0], splitter[2])
            query.answer("✅ Succesfully kicked")
            return ""
        except Exception as err:
            query.answer("❎ Failed to kick")
            context.bot.sendMessage(text="Error: {}".format(err),
                            chat_id=query.message.chat_id,
                            parse_mode=ParseMode.HTML)
    elif splitter[1] == "banned":
        try:
            context.bot.kickChatMember(splitter[0], splitter[2])
            query.answer("✅  Succesfully Banned")
            return ""
        except Exception as err:
            context.bot.sendMessage(text="Error: {}".format(err),
                            chat_id=query.message.chat_id,
                            parse_mode=ParseMode.HTML)
            query.answer("❎ Failed to ban")
    elif splitter[1] == "delete":
        try:
            context.bot.deleteMessage(splitter[0], splitter[3])
            query.answer("✅ Message Deleted")
            return ""
        except Exception as err:
            context.bot.sendMessage(text="Error: {}".format(err),
                            chat_id=query.message.chat_id,
                            parse_mode=ParseMode.HTML)
            query.answer("❎ Failed to delete message!")

def __chat_settings__(chat_id, user_id):
	return user_id, "This chat is setup to send user reports to admins, via /report and @admin: `{}`".format(
		sql.chat_should_report(chat_id))


def __user_settings__(user_id):
	return user_id, "You receive reports from chats you're admin in: `{}`.\nToggle this with /reports in PM.".format(
		sql.user_should_report(user_id))


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)

__mod_name__ = "Reporting"

__help__ = """
 - /report <reason>: reply to a message to report it to admins.
 - @admin: reply to a message to report it to admins.
NOTE: neither of these will get triggered if used by admins

*Admin only:*
 - /reports <on/off>: change report setting, or view current status.
   - If done in pm, toggles your status.
   - If in chat, toggles that chat's status.
"""


REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group, pass_args=True)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = MessageHandler(Filters.regex("(?i)@admin(s)?"), report)
# Callback_Report = CallbackQueryHandler(button, pattern=r"rp_")
# Callback_ReportAsk = CallbackQueryHandler(buttonask, pattern=r"ak_")
report_button_user_handler = CallbackQueryHandler(buttons, pattern=r"report_")

dispatcher.add_handler(report_button_user_handler)
dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
# dispatcher.add_handler(Callback_Report)
# dispatcher.add_handler(Callback_ReportAsk)
