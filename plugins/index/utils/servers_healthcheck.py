import datetime
import time
from threading import Thread

from disco.api.http import APIException
from pony import orm

from plugins.index.utils.changelog import changelog_post_expiration
from plugins.index.utils.discordindex import get_channel_for_name_and_category, update_discord_index
from plugins.index.utils.dms import send_expiration_message
from plugins.index.utils.invite import is_valid_invite

INVITE_CHECK_INTERVAL = 24


@orm.db_session
def start_servers_healthcheck(plugin):
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=INVITE_CHECK_INTERVAL)

    for discord_server in orm.select(ds for ds in plugin.db.DiscordServer if ds.state == 2):
        if cutoff <= discord_server.last_checked:
            continue

        is_expired = False

        try:
            invite = plugin.client.api.invites_get(discord_server.invite_code)
        except APIException:
            is_expired = True

        if invite and not is_valid_invite(plugin, invite, discord_server.invitee_id,
                                          discord_server_entry=discord_server):
            is_expired = True

        discord_server.last_checked = datetime.datetime.now()
        if is_expired:
            discord_server.state = 3
            send_expiration_message(plugin, discord_server)
            changelog_post_expiration(plugin, discord_server)
            plugin.log.info(
                'invite expired '
                'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
                'name: {entry[name]} description: {entry[description]} '
                'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
                'invitee: #{entry[invitee_id]} '
                'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]}'.format(
                    entry=discord_server.to_dict()))

            update_discord_index(plugin, only_in_channel_id=get_channel_for_name_and_category(plugin,
                                                                                              discord_server.category_channel_name,
                                                                                              discord_server.genre_category_name).id)

            orm.commit()


def start_servers_healthcheck_loop(plugin):
    thread = Thread(target=servers_healthcheck_loop, args=(plugin,))
    thread.start()


def servers_healthcheck_loop(plugin):
    while True:
        time.sleep(60 * 60)
        plugin.log.info("starting healthcheck…")
        start_servers_healthcheck(plugin)
