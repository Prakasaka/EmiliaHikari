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

BASE_URL = 'https://del.dog'

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
		context.bot.sendMessage(chat_id, "Goodbye everyone")
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
    summary = f"{wikipedia.summary(reply, sentences=3)}"
    keyboard = [[
            InlineKeyboardButton(
                text="click here for more",
                url=f"{wikipedia.page(reply).url}")
        ]]
    send_message(update.effective_message, summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

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
def paste(update, context):
    message = update.effective_message
    args = context.args

    if message.reply_to_message:
        data = message.reply_to_message.text
    elif len(args) >= 1:
        data = message.text.split(None, 1)[1]
    else:
        send_message(update.effective_message, "What am I supposed to do with this?!")
        return

    r = requests.post(f'{BASE_URL}/documents', data=data.encode('UTF-8'))

    if r.status_code == 404:
        send_message(update.effective_message, 'Failed to reach dogbin')
        r.raise_for_status()

    res = r.json()

    if r.status_code != 200:
        send_message(update.effective_message, res['message'])
        r.raise_for_status()

    key = res['key']
    if res['isUrl']:
        reply = f'Shortened URL: {BASE_URL}/{key}\nYou can view stats, etc. [here]({BASE_URL}/v/{key})'
    else:
        reply = f'{BASE_URL}/{key}'
    send_message(update.effective_message, reply, parse_mode=ParseMode.MARKDOWN)

@run_async
def get_paste_content(update, context):
    message = update.effective_message
    args = context.args

    if len(args) >= 1:
        key = args[0]
    else:
        send_message(update.effective_message, "Please supply a paste key!")
        return

    format_normal = f'{BASE_URL}/'
    format_view = f'{BASE_URL}/v/'

    if key.startswith(format_view):
        key = key[len(format_view):]
    elif key.startswith(format_normal):
        key = key[len(format_normal):]

    r = requests.get(f'{BASE_URL}/raw/{key}')

    if r.status_code != 200:
        try:
            res = r.json()
            send_message(update.effective_message, res['message'])
        except Exception:
            if r.status_code == 404:
                send_message(update.effective_message, 'Failed to reach dogbin')
            else:
                send_message(update.effective_message, 'Unknown error occured')
        r.raise_for_status()

    send_message(update.effective_message, '```' + escape_markdown(r.text) + '```', parse_mode=ParseMode.MARKDOWN)

@run_async
def get_paste_stats(update, context):
    message = update.effective_message
    args = context.args

    if len(args) >= 1:
        key = args[0]
    else:
        send_message(update.effective_message, "Please supply a paste key!")
        return

    format_normal = f'{BASE_URL}/'
    format_view = f'{BASE_URL}/v/'

    if key.startswith(format_view):
        key = key[len(format_view):]
    elif key.startswith(format_normal):
        key = key[len(format_normal):]

    r = requests.get(f'{BASE_URL}/documents/{key}')

    if r.status_code != 200:
        try:
            res = r.json()
            send_message(update.effective_message, res['message'])
        except Exception:
            if r.status_code == 404:
                send_message(update.effective_message, 'Failed to reach dogbin')
            else:
                send_message(update.effective_message, 'Unknown error occured')
        r.raise_for_status()

    document = r.json()['document']
    key = document['_id']
    views = document['viewCount']
    reply = f'Stats for **[/{key}]({BASE_URL}/{key})**:\nViews: `{views}`'
    send_message(update.effective_message, reply, parse_mode=ParseMode.MARKDOWN)


@run_async
def log(update, context):
	message = update.effective_message
	eventdict = message.to_dict()
	jsondump = json.dumps(eventdict, indent=4)
	send_message(update.effective_message, jsondump)


__help__ = """
 - /wiki <text>: search for text written from the wikipedia source
 - /ud <text>: search from urban dictionary
 - /paste: Create a paste or a shortened url using [dogbin](https://del.dog)
 - /getpaste: Get the content of a paste or shortened url from [dogbin](https://del.dog)
 - /pastestats: Get stats of a paste or shortened url from [dogbin](https://del.dog)
"""

__mod_name__ = "special"

GETLINK_HANDLER = CommandHandler("getlink", getlink, pass_args=True, filters=Filters.user(OWNER_ID))
LEAVECHAT_HANDLER = CommandHandler(["leavechat", "leavegroup", "leave"], leavechat, pass_args=True, filters=Filters.user(OWNER_ID))
WIKIPEDIA_HANDLER = DisableAbleCommandHandler("wiki", wiki, pass_args=True)
UD_HANDLER = DisableAbleCommandHandler("ud", urbandictionary)
PASTE_HANDLER = DisableAbleCommandHandler("paste", paste, pass_args=True)
GET_PASTE_HANDLER = DisableAbleCommandHandler("getpaste", get_paste_content, pass_args=True)
PASTE_STATS_HANDLER = DisableAbleCommandHandler("pastestats", get_paste_stats, pass_args=True)
LOG_HANDLER = DisableAbleCommandHandler("log", log, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)
dispatcher.add_handler(WIKIPEDIA_HANDLER)
dispatcher.add_handler(UD_HANDLER)
dispatcher.add_handler(PASTE_HANDLER)
dispatcher.add_handler(GET_PASTE_HANDLER)
dispatcher.add_handler(PASTE_STATS_HANDLER)
dispatcher.add_handler(LOG_HANDLER)