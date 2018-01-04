import datetime

from pony import orm

from plugins.index.utils.changelog import changelog_post_removal, changelog_post_update
from plugins.index.utils.discordindex import update_discord_index, get_channel_for_name_and_category
from plugins.index.utils.queue import update_approval_queue


@orm.db_session
def add_discord_server_to_queue(plugin, invite_code, server_id, server_name, server_description, invitee_id,
                                category_channel_name, genre_category_name):
    plugin.db.DiscordServer(state=1,
                            invite_code=invite_code,
                            server_id=server_id,
                            name=server_name,
                            description=server_description,
                            invitee_id=invitee_id,
                            submitted_at=datetime.datetime.now(),
                            category_channel_name=category_channel_name,
                            genre_category_name=genre_category_name,
                            # index_message_id=789,
                            last_checked=datetime.datetime.now())

    update_approval_queue(plugin)


@orm.db_session
def remove_discord_server(plugin, discord_server, author_user_id, reason=""):
    entry_data = discord_server.to_dict()

    discord_server.delete()

    update_approval_queue(plugin)

    changelog_post_removal(plugin, entry_data, author_user_id, reason)

    index_channel = get_channel_for_name_and_category(plugin, entry_data[
        'category_channel_name'], entry_data['genre_category_name'])
    if index_channel:
        update_discord_index(plugin, only_in_channel_id=index_channel.id)


@orm.db_session
def update_discord_server(plugin, discord_server, attr=None):
    if attr is None:
        attr = {}

    discord_server = plugin.db.DiscordServer[discord_server.id]

    if discord_server.state == 3:
        discord_server.state = 2

    before_data = discord_server.to_dict()

    discord_server.set(**attr)

    after_data = discord_server.to_dict()

    update_approval_queue(plugin)

    changelog_post_update(plugin, before_data, after_data)

    before_channel = get_channel_for_name_and_category(plugin, before_data[
        'category_channel_name'], before_data['genre_category_name'])
    after_channel = get_channel_for_name_and_category(plugin, after_data[
        'category_channel_name'], after_data['genre_category_name'])

    if before_channel:
        update_discord_index(plugin, only_in_channel_id=before_channel.id)
    if after_channel and after_channel.id != before_channel.id:
        update_discord_index(plugin, only_in_channel_id=after_channel.id)
