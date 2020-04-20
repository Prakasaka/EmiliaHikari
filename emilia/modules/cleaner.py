import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html, escape_markdown

from emilia import dispatcher
from emilia.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.log_channel import loggable
from emilia.modules.sql import cleaner_sql as sql
from emilia.modules.connection import connected

from emilia.modules.helper_funcs.alternate import send_message


@run_async
def clean_blue_text_must_click(update, context):
	if sql.is_enable(update.effective_chat.id):
		update.effective_message.delete()

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


__help__ = """
*Admin only:*
 - /cleanbluetext <on/off>: Delete all blue text message.

Note:
- This feature may broke others bot
"""

__mod_name__ = "Cleaner"

SET_CLEAN_BLUE_TEXT_HANDLER = DisableAbleCommandHandler("cleanbluetext", set_blue_text_must_click, pass_args=True)
CLEAN_BLUE_TEXT_HANDLER = MessageHandler(Filters.command & Filters.group, clean_blue_text_must_click)


dispatcher.add_handler(SET_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(CLEAN_BLUE_TEXT_HANDLER, 15)
