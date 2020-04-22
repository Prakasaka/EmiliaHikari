import html
import json
import random
import PIL
import os
import urllib
import datetime
from typing import Optional, List
import time
import urbandict

import pyowm
from pyowm import timeutils, exceptions
import wikipedia
import base64
from bs4 import BeautifulSoup
from emoji import UNICODE_EMOJI

import requests
from telegram.error import BadRequest, Unauthorized
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from emilia.__main__ import STATS, USER_INFO
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.helper_funcs.filters import CustomFilters

from emilia.modules.helper_funcs.alternate import send_message

@run_async
def stickerid(update, context):
	msg = update.effective_message
	if msg.reply_to_message and msg.reply_to_message.sticker:
		send_message(update.effective_message, "Hi {}, sticker id that you reply is :\n```{}```".format(mention_markdown(msg.from_user.id, msg.from_user.first_name), msg.reply_to_message.sticker.file_id),
											parse_mode=ParseMode.MARKDOWN)
	else:
		send_message(update.effective_message, "Please reply to the sticker to get the ID sticker",
											parse_mode=ParseMode.MARKDOWN)

@run_async
def getsticker(update, context):
	msg = update.effective_message
	chat_id = update.effective_chat.id
	if msg.reply_to_message and msg.reply_to_message.sticker:
		send_message(update.effective_message, "Hi " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
											msg.from_user.id) + "Please check the file you requested below."
                                                                                        "\nPlease use this feature wisely!",
											parse_mode=ParseMode.MARKDOWN)
		context.bot.sendChatAction(chat_id, "upload_document")
		file_id = msg.reply_to_message.sticker.file_id
		newFile = context.bot.get_file(file_id)
		newFile.download('sticker.png')
		context.bot.sendDocument(chat_id, document=open('sticker.png', 'rb'))
		context.bot.sendChatAction(chat_id, "upload_photo")
		context.bot.send_photo(chat_id, photo=open('sticker.png', 'rb'))
		
	else:
		send_message(update.effective_message, "Hi " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
											msg.from_user.id) + ", Please reply to the sticker message to get the sticker image",
											parse_mode=ParseMode.MARKDOWN)

@run_async
def stiker(update, context):
	chat_id = update.effective_chat.id
	args = update.effective_message.text.split(None, 1)
	message = update.effective_message
	message.delete()
	if message.reply_to_message:
		context.bot.sendSticker(chat_id, args[1], reply_to_message_id=message.reply_to_message.message_id)
	else:
		context.bot.sendSticker(chat_id, args[1])

@run_async
def file(update, context):
	chat_id = update.effective_chat.id
	args = update.effective_message.text.split(None, 1)
	message = update.effective_message
	message.delete()
	if message.reply_to_message:
		context.bot.sendDocument(chat_id, args[1], reply_to_message_id=message.reply_to_message.message_id)
	else:
		context.bot.sendDocument(chat_id, args[1])

@run_async
def getlink(update, context):
	args = context.args
	if args:
		chat_id = int(args[0])
	else:
		send_message(update.effective_message, "You don't seem to be referring to chat")
	chat = context.bot.getChat(chat_id)
	bot_member = chat.get_member(context.bot.id)
	if bot_member.can_invite_users:
		titlechat = context.bot.get_chat(chat_id).title
		invitelink = context.bot.get_chat(chat_id).invite_link
		send_message(update.effective_message, "Successfully retrieve the invite link in the group {}. \nInvite link : {}".format(titlechat, invitelink))
	else:
		send_message(update.effective_message, "I don't have access to the invitation link!")
	
@run_async
def leavechat(update, context):
	args = context.args
	if args:
		chat_id = int(args[0])
	else:
		send_message(update.effective_message, "You don't seem to be referring to chat")
	try:
		chat = context.bot.getChat(chat_id)
		titlechat = context.bot.get_chat(chat_id).title
		context.bot.sendMessage(chat_id, "Goodbye everyone 😁")
		context.bot.leaveChat(chat_id)
		send_message(update.effective_message, "I have left the group {}").format(titlechat)

	except BadRequest as excp:
		if excp.message == "Chat not found":
			send_message(update.effective_message, "Looks like I have been out or kicked in the group")
		else:
			return


@run_async
def wiki(update, context):
    args = context.args
    reply = " ".join(args)
    summary = f"{wikipedia.summary(reply, sentences=3)} [More]({wikipedia.page(reply).url})"
    send_message(update.effective_message, summary, parse_mode=ParseMode.MARKDOWN)

@run_async
def urbandictionary(update, context):
    message = update.effective_message
    text = message.text[len('/ud '):]
    results = requests.get(f'http://api.urbandictionary.com/v0/define?term={text}').json()
    try:
        reply_text = f'*{text}*\n\n{results["list"][0]["definition"]}\n\n_{results["list"][0]["example"]}_'
    except:
        reply_text = "No results found."
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN)


@run_async
def log(update, context):
	message = update.effective_message
	eventdict = message.to_dict()
	jsondump = json.dumps(eventdict, indent=4)
	send_message(update.effective_message, jsondump)

def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')


__help__ = """
 - /stickerid: reply message sticker at PM to get ID sticker
 - /wiki <text>: search for text written from the wikipedia source
 - /ud <text>: search from urban dictionary
"""

__mod_name__ = "special"

STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
#GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)
STIKER_HANDLER = CommandHandler("stiker", stiker, filters=Filters.user(OWNER_ID))
FILE_HANDLER = CommandHandler("file", file, filters=Filters.user(OWNER_ID))
GETLINK_HANDLER = CommandHandler("getlink", getlink, pass_args=True, filters=Filters.user(OWNER_ID))
LEAVECHAT_HANDLER = CommandHandler(["leavechat", "leavegroup", "leave"], leavechat, pass_args=True, filters=Filters.user(OWNER_ID))
WIKIPEDIA_HANDLER = DisableAbleCommandHandler("wiki", wiki, pass_args=True)
UD_HANDLER = DisableAbleCommandHandler("ud", urbandictionary)
LOG_HANDLER = DisableAbleCommandHandler("log", log, filters=Filters.user(OWNER_ID))

#dispatcher.add_handler(PING_HANDLER)
dispatcher.add_handler(STICKERID_HANDLER)
#dispatcher.add_handler(GETSTICKER_HANDLER)
dispatcher.add_handler(STIKER_HANDLER)
dispatcher.add_handler(FILE_HANDLER)
dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)
dispatcher.add_handler(WIKIPEDIA_HANDLER)
dispatcher.add_handler(UD_HANDLER)
dispatcher.add_handler(LOG_HANDLER)