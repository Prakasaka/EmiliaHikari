import html
import json
import random
from datetime import datetime
from typing import Optional, List
import time
import locale

import requests
from telegram.error import BadRequest, Unauthorized
from telegram import Message, Chat, Update, Bot, MessageEntity, InlineKeyboardMarkup
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from emilia.__main__ import STATS, USER_INFO
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia.modules.helper_funcs.msg_types import get_message_type
from emilia.modules.helper_funcs.misc import build_keyboard_alternate

import emilia.modules.sql.feds_sql as feds_sql
from emilia.modules.helper_funcs.alternate import send_message


MARKDOWN_HELP: """
Markdown is a very powerful formatting tool supported by telegram. {} has some enhancements, to make sure that \
saved messages are correctly parsed, and to allow you to create buttons.
- <code>_italic_</code>: wrapping text with '_' will produce italic text
- <code>*bold*</code>: wrapping text with '*' will produce bold text
- <code>`code`</code>: wrapping text with '`' will produce monospaced text, also known as 'code'
- <code>[sometext](someURL)</code>: this will create a link - the message will just show <code>sometext</code>, \
and tapping on it will open the page at <code>someURL</code>.
EG: <code>[test](example.com)</code>
- <code>[buttontext](buttonurl:someURL)</code>: this is a special enhancement to allow users to have telegram \
buttons in their markdown. <code>buttontext</code> will be what is displayed on the button, and <code>someurl</code> \
will be the url which is opened.
EG: <code>[This is a button](buttonurl:example.com)</code>
If you want multiple buttons on the same line, use :same, as such:
<code>[one](buttonurl:example.com)
[two](buttonurl:google.com:same)</code>
This will create two buttons on a single line, instead of one button per line.
Keep in mind that your message <b>MUST</b> contain some text other than just a button!
"""


RUN_STRINGS = (
    "Where do you think you're going?",
    "Huh? what? did they get away?",
    "ZZzzZZzz... Huh? what? oh, just them again, nevermind.",
    "Get back here!",
    "Not so fast...",
    "Look out for the wall!",
    "Don't leave me alone with them!!",
    "You run, you die.",
    "Jokes on you, I'm everywhere",
    "You're gonna regret that...",
    "You could also try /kickme, I hear that's fun.",
    "Go bother someone else, no-one here cares.",
    "You can run, but you can't hide.",
    "Is that all you've got?",
    "I'm behind you...",
    "You've got company!",
    "We can do this the easy way, or the hard way.",
    "You just don't get it, do you?",
    "Yeah, you better run!",
    "Please, remind me how much I care?",
    "I'd run faster if I were you.",
    "That's definitely the droid we're looking for.",
    "May the odds be ever in your favour.",
    "Famous last words.",
    "And they disappeared forever, never to be seen again.",
    "\"Oh, look at me! I'm so cool, I can run from a bot!\" - this person",
    "Yeah yeah, just tap /kickme already.",
    "Here, take this ring and head to Mordor while you're at it.",
    "Legend has it, they're still running...",
    "Unlike Harry Potter, your parents can't protect you from me.",
    "Fear leads to anger. Anger leads to hate. Hate leads to suffering. If you keep running in fear, you might "
    "be the next Vader.",
    "Multiple calculations later, I have decided my interest in your shenanigans is exactly 0.",
    "Legend has it, they're still running.",
    "Keep it up, not sure we want you here anyway.",
    "You're a wiza- Oh. Wait. You're not Harry, keep moving.",
    "NO RUNNING IN THE HALLWAYS!",
    "Hasta la vista, baby.",
    "Who let the dogs out?",
    "It's funny, because no one cares.",
    "Ah, what a waste. I liked that one.",
    "Frankly, my dear, I don't give a damn.",
    "My milkshake brings all the boys to yard... So run faster!",
    "You can't HANDLE the truth!",
    "A long time ago, in a galaxy far far away... Someone would've cared about that. Not anymore though.",
    "Hey, look at them! They're running from the inevitable banhammer... Cute.",
    "Han shot first. So will I.",
    "What are you running after, a white rabbit?",
    "As The Doctor would say... RUN!",
    "Run Barry run",
    "Don't you want VoLTE ?",
    "Oh! Someone wants to be The Flash",
    "Nani the F***!",
    "You run, you lose.",
    "Go watch POGO!",
    "Pew Pew Pew...",
    "You think speed is your ally? I was born on treadmill.",
    "A shinigami is coming after you.",
)

SLAP_TEMPLATES = (
    "{user1} {hits} {user2} with a {item}.",
    "{user1} {hits} {user2} in the face with a {item}.",
    "{user1} {hits} {user2} around a bit with a {item}.",
    "{user1} {throws} a {item} at {user2}.",
    "{user1} grabs a {item} and {throws} it at {user2}'s face.",
    "{user1} launches a {item} in {user2}'s general direction.",
    "{user1} starts slapping {user2} silly with a {item}.",
    "{user1} pins {user2} down and repeatedly {hits} them with a {item}.",
    "{user1} grabs up a {item} and {hits} {user2} with it.",
    "{user1} ties {user2} to a chair and {throws} a {item} at them.",
    "{user1} gave a friendly push to help {user2} learn to swim in lava."
    "{user1} says HAKAI,{user2} gets destroyed. No one can escape from power of the god of destruction.",
    "{user1} blasts {user2} with a spirit bomb.",
    "{user1} throws a Kamehameha wave at {user2}.",
    "{user1} cuts {user2} into pieces using Destructo Discs.",
    "{user1} snaps his fingers causing {user2} to disintegrate from the universe.",
    "{user1} craves {user2} in the Death Note.",
)

ITEMS = (
    "cast iron skillet",
    "large trout",
    "baseball bat",
    "cricket bat",
    "wooden cane",
    "nail",
    "printer",
    "shovel",
    "CRT monitor",
    "physics textbook",
    "toaster",
    "portrait of Richard Stallman",
    "television",
    "five ton truck",
    "roll of duct tape",
    "book",
    "laptop",
    "old television",
    "sack of rocks",
    "rainbow trout",
    "rubber chicken",
    "spiked bat",
    "fire extinguisher",
    "heavy rock",
    "chunk of dirt",
    "beehive",
    "piece of rotten meat",
    "bear",
    "ton of bricks",
)

THROW = (
    "throws",
    "flings",
    "chucks",
    "hurls",
)

HIT = (
    "hits",
    "whacks",
    "slaps",
    "smacks",
    "bashes",
)


@run_async
def runs(update, context):
    send_message(update.effective_message, random.choice("RUN_STRINGS"))

@run_async
def slap(update, context):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    #if msg.from_user.username:
    #    curr_user = "@" + escape_markdown(msg.from_user.username)
    #else:
    curr_user = "{}".format(mention_markdown(msg.from_user.id, msg.from_user.first_name))

    user_id = extract_user(update.effective_message, args)
    if user_id and user_id != "error":
        slapped_user = context.bot.get_chat(user_id)
        user1 = curr_user
        #if slapped_user.username:
        #    user2 = "@" + escape_markdown(slapped_user.username)
        #else:
        user2 = "{}".format(mention_markdown(slapped_user.id, slapped_user.first_name))

    # if no target found, bot targets the sender
    else:
        user1 = "{}".format(mention_markdown(context.bot.id, context.bot.first_name))
        user2 = curr_user

    temp = random.choice("SLAP_TEMPLATES")
    item = random.choice("ITEMS")
    hit = random.choice("HIT")
    throw = random.choice("THROW")

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    send_message(update.effective_message, repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_id(update, context):
    args = context.args
    user_id = extract_user(update.effective_message, args)
    if user_id and user_id != "error":
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            text = "The original sender, {}, has an ID of `{}`.\nThe forwarder, {}, has an ID of `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id)
            if update.effective_message.chat.type != "private":
                text += "\n" + "This group's id is `{}`.".format(update.effective_message.chat.id)
            send_message(update.effective_message, 
                text,
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = context.bot.get_chat(user_id)
            text = "{}'s id is `{}`.".format(escape_markdown(user.first_name), user.id)
            if update.effective_message.chat.type != "private":
                text += "\n" + "This group's id is `{}`.".format(update.effective_message.chat.id)
            send_message(update.effective_message, text,
                                                parse_mode=ParseMode.MARKDOWN)
    elif user_id == "error":
        try:
            user = context.bot.get_chat(args[0])
        except BadRequest:
            send_message(update.effective_message, "Error: Unknown User/Chat!")
            return
        text = "Your id is `{}`.".format(update.effective_message.from_user.id)
        text += "\n" + "This group's id is `{}`.".format(user.id)
        if update.effective_message.chat.type != "private":
            text += "\n" + "This group's id is `{}`.".format(update.effective_message.chat.id)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            send_message(update.effective_message, "Your id is `{}`.".format(update.effective_message.from_user.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            send_message(update.effective_message, "Your id is `{}`.".format(update.effective_message.from_user.id) + "\n" + "This group's id is `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(update, context):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user_id = extract_user(update.effective_message, args)

    if user_id and user_id != "error":
        user = context.bot.get_chat(user_id)

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        send_message(update.effective_message, "I can't extract a user from this.")
        return

    else:
        return

    text = "<b>User info</b>:" \
           + "\nID: <code>{}</code>".format(user.id) + \
           "\nFirst Name: {}".format(html.escape(user.first_name))

    if user.last_name:
        text += "\nLast Name: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nUsername: @{}".format(html.escape(user.username))

    text += "\nPermanent user link: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\nThis person is my owner - I would never do anything against them!"
    else:
        if user.id in SUDO_USERS:
            text += "\n\nThis person is one of my sudo users! Nearly as powerful as my owner - so watch it."
        else:
            if user.id in SUPPORT_USERS:
                text += "\n\nThis person is one of my support users! Not quite a sudo user, but can still gban you off the map."

            if user.id in WHITELIST_USERS:
                text += "\n\nThis person has been whitelisted! That means I'm not allowed to ban/kick them."

    fedowner = feds_sql.get_user_owner_fed_name(user.id)
    if fedowner:
        text += "\n\n<b>This user is a owner fed in the current federation:</b>\n<code>"
        text += "</code>, <code>".join(fedowner)
        text += "</code>"
    # fedadmin = feds_sql.get_user_admin_fed_name(user.id)
    # if fedadmin:
    #     text += tl(update.effective_message, "\n\nThis user is a fed admin in the current federation:\n")
    #     text += ", ".join(fedadmin)

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id, chat.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    send_message(update.effective_message, text, parse_mode=ParseMode.HTML)

@run_async
def echo(update, context):
    message = update.effective_message
    chat_id = update.effective_chat.id
    try:
        message.delete()
    except BadRequest:
        pass
    # Advanced
    text, data_type, content, buttons = get_message_type(message)
    tombol = build_keyboard_alternate(buttons)
    if str(data_type) in ('Types.BUTTON_TEXT', 'Types.TEXT'):
        try:
            if message.reply_to_message:
                context.bot.send_message(chat_id, text, parse_mode="markdown", reply_to_message_id=message.reply_to_message.message_id, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(tombol))
            else:
                context.bot.send_message(chat_id, text, quote=False, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(tombol))
        except BadRequest:
            context.bot.send_message(chat_id, "Wrong markdown text! If you don't know what markdown is, please type `/markdownhelp` in PM.", parse_mode="markdown")
            return


@run_async
def markdown_help(update, context):
    send_message(update.effective_message, MARKDOWN_HELP.format(dispatcher.bot.first_name), parse_mode=ParseMode.HTML)
    send_message(update.effective_message, "Try forwarding the following message to me, and you'll see!")
    send_message(update.effective_message, "/save test This is a markdown test. _italics_, *bold*, `code`, [URL](example.com) [button](buttonurl:github.com) [button2](buttonurl:google.com:same)")


@run_async
def stats(update, context):
    send_message(update.effective_message, "Current stats:\n" + "\n".join([mod.__stats__() for mod in STATS]))


# /ip is for private use
__help__ = """
 - /id: get the current group id. If used by replying to a message, gets that user's id.
 - /runs: reply a random string from an array of replies.
 - /slap: slap a user, or get slapped if not a reply.
 - /info: get information about a user.
 - /markdownhelp: quick summary of how markdown works in telegram - can only be called in private chats.
"""

__mod_name__ = "Misc"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler(["runs", "lari"], runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
