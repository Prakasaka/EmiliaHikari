import math
import os
import urllib.request as urllib
from typing import List

from PIL import Image
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import TelegramError
from telegram import Update, bot
from telegram.ext import run_async
from telegram.utils.helpers import escape_markdown

from emilia import dispatcher
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.alternate import send_message


@run_async
def stickerid(update, context):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        send_message(update.effective_message, "Sticker ID:\n```" +
                                            escape_markdown(msg.reply_to_message.sticker.file_id) + "```",
                                            parse_mode=ParseMode.MARKDOWN)
    else:
        send_message(update.effective_message, "Please reply to a sticker to get its ID.")


@run_async
def getsticker(update, context):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
        new_file = context.bot.get_file(file_id)
        new_file.download('sticker.png')
        context.bot.send_document(chat_id, document=open('sticker.png', 'rb'))
        os.remove("sticker.png")
    else:
        send_message(update.effective_message, "Please reply to a sticker for me to upload its PNG.")


@run_async
def kang(update, context):
    msg = update.effective_message
    chat = update.effective_chat
    args = context.args
    user = update.effective_user
    packnum = 0
    packname = "c" + str(user.id) + "_by_" + context.bot.username
    packname_found = 0
    max_stickers = 120
    while packname_found == 0:
        try:
            stickerset = context.bot.get_sticker_set(packname)
            if len(stickerset.stickers) >= max_stickers:
                packnum += 1
                packname = "c" + str(packnum) + "_" + str(
                    user.id) + "_by_" + context.bot.username
            else:
                packname_found = 1
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                packname_found = 1
    kangsticker = "images/kangsticker.png"
    if msg.reply_to_message:
        if msg.reply_to_message.sticker:
            file_id = msg.reply_to_message.sticker.file_id
        elif msg.reply_to_message.photo:
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.document:
            file_id = msg.reply_to_message.document.file_id
        else:
            send_message(update.effective_message, "Yea, I can't kang that")
        kang_file = context.bot.get_file(file_id)
        kang_file.download('images/kangsticker.png')
        if args:
            sticker_emoji = str(args[0])
        elif msg.reply_to_message.sticker and msg.reply_to_message.sticker.emoji:
            sticker_emoji = msg.reply_to_message.sticker.emoji
        else:
            sticker_emoji = "🤔"
        try:
            im = Image.open(kangsticker)
            maxsize = (512, 512)
            if (im.width and im.height) < 512:
                size1 = im.width
                size2 = im.height
                if im.width > im.height:
                    scale = 512 / size1
                    size1new = 512
                    size2new = size2 * scale
                else:
                    scale = 512 / size2
                    size1new = size1 * scale
                    size2new = 512
                size1new = math.floor(size1new)
                size2new = math.floor(size2new)
                sizenew = (size1new, size2new)
                im = im.resize(sizenew)
            else:
                im.thumbnail(maxsize)
            if not msg.reply_to_message.sticker:
                im.save(kangsticker, "PNG")
            context.bot.add_sticker_to_set(user_id=user.id,
                                   name=packname,
                                   png_sticker=open('images/kangsticker.png', 'rb'),
                                   emojis=sticker_emoji)
            send_message(update.effective_message, 'added to [pack](t.me/addstickers/{}). Emoji: {}'.format(
                packname, sticker_emoji),
                           parse_mode=ParseMode.MARKDOWN)
        except OSError as e:
            send_message(update.effective_message, 'I can only kang images!')
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                makepack_internal(msg, user, open('images/kangsticker.png', 'rb'),
                                  sticker_emoji, context.bot, packname, packnum, chat)
            elif e.message == "Sticker_png_dimensions":
                im.save(kangsticker, "PNG")
                context.bot.add_sticker_to_set(user_id=user.id,
                                       name=packname,
                                       png_sticker=open(
                                           'images/kangsticker.png', 'rb'),
                                       emojis=sticker_emoji)
                send_message(update.effective_message, 'added to [pack](t.me/addstickers/{}). Emoji: {}'.format(
                    packname, sticker_emoji),
                               parse_mode=ParseMode.MARKDOWN)
            elif e.message == "Invalid sticker emojis":
                send_message(update.effective_message, "Error: Invalid emoji(s).")
            elif e.message == "Stickers_too_much":
                send_message(update.effective_message, "Error: Max packsize reached. Press F to pay respecc.")
            elif e.message == "Internal Server Error: sticker set not found (500)":
                send_message(update.effective_message, 'added to [pack](t.me/addstickers/{}). Emoji: {}'.format(
                    packname, sticker_emoji),
                               parse_mode=ParseMode.MARKDOWN)
            print(e)
    elif args:
        try:
            try:
                urlemoji = msg.text.split(" ")
                png_sticker = urlemoji[1]
                sticker_emoji = urlemoji[2]
            except IndexError:
                sticker_emoji = "🤔"
            urllib.urlretrieve(png_sticker, kangsticker)
            im = Image.open(kangsticker)
            maxsize = (512, 512)
            if (im.width and im.height) < 512:
                size1 = im.width
                size2 = im.height
                if im.width > im.height:
                    scale = 512 / size1
                    size1new = 512
                    size2new = size2 * scale
                else:
                    scale = 512 / size2
                    size1new = size1 * scale
                    size2new = 512
                size1new = math.floor(size1new)
                size2new = math.floor(size2new)
                sizenew = (size1new, size2new)
                im = im.resize(sizenew)
            else:
                im.thumbnail(maxsize)
            im.save(kangsticker, "PNG")
            msg.reply_photo(photo=open('images/kangsticker.png', 'rb'))
            context.bot.add_sticker_to_set(user_id=user.id,
                                   name=packname,
                                   png_sticker=open('images/kangsticker.png', 'rb'),
                                   emojis=sticker_emoji)
            send_message(update.effective_message, 'added to [pack](t.me/addstickers/{}). Emoji: {}'.format(
                packname, sticker_emoji),
                           parse_mode=ParseMode.MARKDOWN)
        except OSError as e:
            send_message(update.effective_message, 'I can only kang images!')
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                makepack_internal(msg, user, open('images/kangsticker.png', 'rb'),
                                  sticker_emoji, context.bot, packname, packnum, chat)
            elif e.message == "Sticker_png_dimensions":
                im.save(kangsticker, "PNG")
                context.bot.add_sticker_to_set(user_id=user.id,
                                       name=packname,
                                       png_sticker=open(
                                           'images/kangsticker.png', 'rb'),
                                       emojis=sticker_emoji)
                send_message(update.effective_message, 'added to [pack](t.me/addstickers/{}). Emoji: {}'.format(
                    packname, sticker_emoji),
                               parse_mode=ParseMode.MARKDOWN)
            elif e.message == "Invalid sticker emojis":
                send_message(update.effective_message, "Error: Invalid emoji(s).")
            elif e.message == "Stickers_too_much":
                send_message(update.effective_message, "Error: Max packsize reached. Press F to pay respecc.")
            elif e.message == "Internal Server Error: sticker set not found (500)":
                send_message(update.effective_message, 'added to [pack](t.me/addstickers/{}). Emoji: {}'.format(
                    packname, sticker_emoji),
                               parse_mode=ParseMode.MARKDOWN)
            print(e)
    else:
        packs = 'Please reply to a sticker or an image to kang it!\nOh, by the way. here are your packs:\n')
        if packnum > 0:
            firstpackname = "c" + str(user.id) + "_by_" + context.bot.username
            for i in range(0, packnum + 1):
                if i == 0:
                    packs += f"[pack](t.me/addstickers/{firstpackname})\n"
                else:
                    packs += f"[pack{i}](t.me/addstickers/{packname})\n"
        else:
            packs += f"[pack](t.me/addstickers/{packname})"
        msg.reply_text(packs, parse_mode=ParseMode.MARKDOWN)
    if os.path.isfile("images/kangsticker.png"):
        os.remove("images/kangsticker.png")


def makepack_internal(msg, user, png_sticker, emoji, bot, packname, packnum,
                      chat):
    name = user.first_name
    name = name[:50]
    try:
        extra_version = ""
        if packnum > 0:
            extra_version = " " + str(packnum)
        success = context.bot.create_new_sticker_set(user.id,
                                             packname,
                                             f"{name}s haruka pack" +
                                             extra_version,
                                             png_sticker=png_sticker,
                                             emojis=emoji)
    except TelegramError as e:
        print(e)
        if e.message == "Sticker set name is already occupied":
            send_message(update.effective_message, f"Your pack can be found [here](t.me/addstickers/{packname})",
                           parse_mode=ParseMode.MARKDOWN)
        elif e.message == "Peer_id_invalid":
            send_message(update.effective_message, "Contact me in PM first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                text="Start", url=f"t.me/{context.bot.username}")]]))
        return

    if success:
        send_message(update.effective_message,
                           f"Sticker pack successfully created. Get it [here](t.me/addstickers/{packname})",
                       parse_mode=ParseMode.MARKDOWN)
    else:
        send_message(update.effective_message, "Failed to create sticker pack. Possibly due to blek mejik.")


__help__ = """
- /stickerid: reply to a sticker to me to tell you its file ID.
- /getsticker: reply to a sticker to me to upload its raw PNG file.
- /kang: reply to a sticker to add it to your pack.
"""

__mod_name__ = "Stickers"
STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)
KANG_HANDLER = DisableAbleCommandHandler("kang", kang, pass_args=True, admin_ok=True)

dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
dispatcher.add_handler(KANG_HANDLER)