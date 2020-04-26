import html
import PIL
import traceback
from contextlib import redirect_stdout
from typing import Optional, List
import urbandict
import pyowm
from pyowm import timeutils, exceptions
import wikipedia
import base64
from bs4 import BeautifulSoup

import sys
import inspect
import os
import shutil
import glob
import math
import textwrap
import os
import requests
import json
import gc
import datetime
import time
import traceback
import re
import io
import asyncio
import random
import subprocess
import urllib
import psutil

from typing import Optional, List
from telegram.error import BadRequest, Unauthorized
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, run_async, Filters, MessageHandler
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, LOGGER
from emilia.__main__ import STATS, USER_INFO
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.helper_funcs.filters import CustomFilters

from emilia.modules.helper_funcs.alternate import send_message
from telegraph import Telegraph, upload_file

BASE_URL = 'https://del.dog'
namespaces = {}


def namespace_of(chat, update, context):
    if chat not in namespaces:
        namespaces[chat] = {
            '__builtins__': globals()['__builtins__'],
            'context.bot': context.bot,
            'effective_message': update.effective_message,
            'effective_user': update.effective_user,
            'effective_chat': update.effective_chat,
            'update': update
        }

    return namespaces[chat]


def log_input(update):
    user = update.effective_user.id
    chat = update.effective_chat.id
    LOGGER.info(f"IN: {update.effective_message.text} (user={user}, chat={chat})")


def send(msg, update, context):
    LOGGER.info(f"OUT: '{msg}'")
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"`{msg}`", parse_mode=ParseMode.MARKDOWN)


@run_async
def evaluate(update, context):
    send(do(eval, update, context), update, context)


@run_async
def execute(update, context):
    send(do(exec, update, context), update, context)


def cleanup_code(code):
    if code.startswith('```') and code.endswith('```'):
        return '\n'.join(code.split('\n')[1:-1])
    return code.strip('` \n')


def do(func, update, context):
    log_input(update)
    content = update.message.text.split(' ', 1)[-1]
    body = cleanup_code(content)
    env = namespace_of(update.message.chat_id, update, context)

    os.chdir(os.getcwd())
    with open(os.path.join(os.getcwd(), 'emilia/modules/helper_funcs/temp.txt'), 'w') as temp:
        temp.write(body)

    stdout = io.StringIO()

    to_compile = f'def func():\n{textwrap.indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return f'{e.__class__.__name__}: {e}'

    func = env['func']

    try:
        with redirect_stdout(stdout):
            func_return = func()
    except Exception as e:
        value = stdout.getvalue()
        return f'{value}{traceback.format_exc()}'
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f'{value}'
            else:
                try:
                    result = f'{repr(eval(body, env))}'
                except:
                    pass
        else:
            result = f'{value}{func_return}'
        if result:
            if len(str(result)) > 5000:
                result = 'Output is too long'
            return result


@run_async
def clear(update, context):
    log_input(update)
    global namespaces
    if update.message.chat_id in namespaces:
        del namespaces[update.message.chat_id]
    send("Cleared locals.", update, context)

@run_async
def post_telegraph(update, context):
    args = context.args
    short_name = "Created By @MidukkiBot 😬"
    msg = update.effective_message # type: Optional[Message]
    telegraph = Telegraph()
    r = telegraph.create_account(short_name=short_name)
    auth_url = r["auth_url"]
    LOGGER.info(auth_url)
    title_of_page = " ".join(args)
    page_content = msg.reply_to_message.text
    page_content = page_content.replace("\n", "<br>")
    response = telegraph.create_page(
        title_of_page,
        html_content=page_content
    )
    send_message(update.effective_message, "https://telegra.ph/{}".format(response["path"]))


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
    try:
        reply = " ".join(args)
        summary = f"{wikipedia.summary(reply, sentences=3)}"
        keyboard = [[
            InlineKeyboardButton(
                text="click here for read more",
                url=f"{wikipedia.page(reply).url}")
        ]]
        send_message(update.effective_message, summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    except wikipedia.PageError as e:
        send_message(update.effective_message, "Error: {}".format(e))
    except BadRequest as et:
        send_message(update.effective_message, "Error: {}".format(et))
    except wikipedia.exceptions.DisambiguationError as eet:
        send_message(update.effective_message, 
                "Error\n There are too many query! Express it more!\nPossible query result:\n{}"
                .format(eet))

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
 - /tele <text> - as reply to a long message
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
eval_handler = CommandHandler('eval', evaluate, filters=Filters.user(OWNER_ID))
exec_handler = CommandHandler('py', execute, filters=Filters.user(OWNER_ID))
clear_handler = CommandHandler('clearlocals', clear, filters=Filters.user(OWNER_ID))
dispatcher.add_handler(DisableAbleCommandHandler("tele", post_telegraph, pass_args=True))

dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)
dispatcher.add_handler(WIKIPEDIA_HANDLER)
dispatcher.add_handler(UD_HANDLER)
dispatcher.add_handler(PASTE_HANDLER)
dispatcher.add_handler(GET_PASTE_HANDLER)
dispatcher.add_handler(PASTE_STATS_HANDLER)
dispatcher.add_handler(LOG_HANDLER)
dispatcher.add_handler(eval_handler)
dispatcher.add_handler(exec_handler)
dispatcher.add_handler(clear_handler)