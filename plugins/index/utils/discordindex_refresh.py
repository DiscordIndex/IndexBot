import time
from threading import Thread

from pony import orm

from plugins.index.utils.discordindex import update_discord_index


@orm.db_session
def start_discordindex_refresh(plugin):
    for channel_id in plugin.config.emojiChannelIDs:
        update_discord_index(plugin, only_in_channel_id=channel_id)


def start_discordindex_refresh_loop(plugin):
    thread = Thread(target=discordindex_refresh_loop, args=(plugin,))
    thread.start()


def discordindex_refresh_loop(plugin):
    while True:
        time.sleep(60 * 60)
        plugin.log.info("starting discord index refresh…")
        start_discordindex_refresh(plugin)
