from functools import wraps
from typing import Optional

from emilia import OWNER_ID
from emilia.modules.helper_funcs.misc import is_module_loaded

from emilia.modules.helper_funcs.alternate import send_message

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode, Message, Chat
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async
    from telegram.utils.helpers import escape_markdown

    from emilia import dispatcher, LOGGER
    from emilia.modules.helper_funcs.chat_status import user_admin
    from emilia.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(update, context, *args, **kwargs):
            result = func(update, context, *args, **kwargs)
            chat = update.effective_chat  # type: Optional[Chat]
            message = update.effective_message  # type: Optional[Message]
            if result:
                if chat.type == chat.SUPERGROUP and chat.username:
                    result += "\n<b>Link:</b> " \
                              "<a href=\"http://telegram.me/{}/{}\">Click here</a>".format(chat.username,
                                                                                           message.message_id)
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    try:
                        send_log(context.bot, log_chat, chat.id, result)
                    except Unauthorized:
                        sql.stop_chat_logging(chat.id)
            elif result == "":
                pass
            else:
                LOGGER.warning("%s was set as loggable, but had no return statement.", func)

            return result

        return log_action


    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):
        try:
            bot.send_message(log_chat_id, result, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(orig_chat_id, "This log channel has been deleted - unsetting.")
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Could not parse")

                bot.send_message(log_chat_id, result + "\n\nFormatting has been disabled due to an unexpected error.")


    @run_async
    @user_admin
    def logging(update, context):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = context.bot.get_chat(log_channel)
            send_message(update.effective_message, "This group has all it's logs sent to: {} (`{}`)".format(escape_markdown(log_channel_info.title), log_channel),parse_mode=ParseMode.MARKDOWN)

        else:
            send_message(update.effective_message, "No log channel has been set for this group!")


    @run_async
    @user_admin
    def setlog(update, context):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == chat.CHANNEL:
            send_message(update.effective_message, "Now, forward the /setlog to the group you want to tie this channel to!")

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error deleting message in log channel. Should work anyway though.")
                    
            try:
                context.bot.send_message(message.forward_from_chat.id, "This channel has been set as the log channel for {}.".format(chat.title or chat.first_name))
            except Unauthorized as excp:
                if excp.message == "Forbidden: bot is not a member of the channel chat":
                    context.bot.send_message(chat.id, "Failed to set the log channel!\nI might not be the admin on the channel.")
                    sql.stop_chat_logging(chat.id)
                    return
                else:
                    LOGGER.exception("ERROR in setting the log channel.")
                    
            context.bot.send_message(chat.id, "Successfully set log channel!")

        else:
            send_message(update.effective_message, "The steps to set a log channel are:\n - add bot to the desired channel\n - send /setlog to the channel\n - forward the /setlog to the group\n")


    @run_async
    @user_admin
    def unsetlog(update, context):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            context.bot.send_message(log_channel, "Channel has been unlinked from {}".format(chat.title))
            send_message(update.effective_message, "Log channel has been un-set.")

        else:
            send_message(update.effective_message, "No log channel has been set yet!")


    def __stats__():
        return OWNER_ID, "{} log channels set.".format(sql.num_logchannels())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return user_id, "This group has all it's logs sent to: {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                            log_channel)
        return user_id, "No log channel is set for this group!"


    __help__ = """
*Admin only:*
- /logchannel: get log channel info
- /setlog: set the log channel.
- /unsetlog: unset the log channel.

Setting the log channel is done by:
- adding the bot to the desired channel (as an admin!)
- sending /setlog in the channel
- forwarding the /setlog to the group
"""

    __mod_name__ = "Channel Log"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func
