from disco.bot import Plugin
from disco.types.channel import Channel as DiscoChannel
from pony import orm

from db import DbHandler
from plugins.index.utils.index import add_discord_server_to_queue, remove_discord_server, update_discord_server
from plugins.index.utils.invite import extract_invite_code, is_valid_invite
from .config import IndexPluginConfig


@Plugin.with_config(IndexPluginConfig)
class IndexPlugin(Plugin):
    def __init__(self, bot, config):
        super().__init__(bot, config)
        self.db = DbHandler().getDb()

    def load(self, ctx):
        super(IndexPlugin, self).load(ctx)

    @Plugin.command('channels')  # TODO: level
    def command_ping(self, event):
        event.msg.reply('Add Channels: <#' + ">, <#".join(str(x) for x in self.config.addChannelIDs) + '>')

    @orm.db_session
    @Plugin.command('add',
                    '<invite:str> <category_channel:channel|snowflake> <name_and_description:str...>',
                    aliases=['submit'])  # TODO: level
    def command_add(self, event, invite, category_channel, name_and_description):
        if event.msg.channel.id not in self.config.addChannelIDs:
            return

        self.client.api.channels_typing(event.msg.channel.id)

        name = name_and_description.strip()
        description = ""
        if "|" in name:
            parts = name.split('|', 2)
            name = parts[0].strip()
            description = parts[1].strip()

        if len(name) > 32:
            event.msg.reply('name too long')
            return

        if len(description) > 100:
            event.msg.reply('description too long')
            return

        invite_code = extract_invite_code(invite)
        if len(invite_code) <= 0:
            event.msg.reply('no invite code found')
            return

        invite = self.client.api.invites_get(invite_code)

        if orm.select(
                orm.count(ds) for ds in self.db.DiscordServer if ds.server_id == invite.guild.id).first() > 0:
            event.msg.reply('server already in the index or queue')
            return

        if not is_valid_invite(self.client, invite, event.msg.author.id):
            event.msg.reply('invalid invite code')
            return

        if not isinstance(category_channel, DiscoChannel):
            category_channel = self.state.channels.get(category_channel)

        if category_channel is None or category_channel.guild_id != event.msg.channel.guild_id:
            event.msg.reply('invalid category channel')
            return

        genre_category_name = ""
        if category_channel.parent is not None:
            genre_category_name = category_channel.parent.name

        add_discord_server_to_queue(self.db, invite_code, invite.guild.id, name, description, event.msg.author.id,
                                    category_channel.name, genre_category_name)

        event.msg.reply('Added to queue!')

    @orm.db_session
    @Plugin.command('remove',
                    '<invite:str>',
                    aliases=['delete', 'withdraw'])  # TODO: level
    def command_remove(self, event, invite):
        if event.msg.channel.id not in self.config.addChannelIDs:
            return

        self.client.api.channels_typing(event.msg.channel.id)

        invite_code = extract_invite_code(invite)
        if len(invite_code) <= 0:
            event.msg.reply('no invite code found')
            return

        discord_servers_found = orm.select(ds for ds in self.db.DiscordServer if ds.invite_code == invite_code)
        if discord_servers_found.count() <= 0:
            event.msg.reply('invite not found in queue or index')
            return

        # TODO: add exception for staff
        if discord_servers_found.first().invitee_id != event.msg.author.id:
            event.msg.reply('you can only remove entries your submitted yourself')
            return

        remove_discord_server(discord_servers_found.first())

        event.msg.reply('Removed!')

    @orm.db_session
    @Plugin.command('update',
                    '<invite:str> [category_channel:channel|snowflake] [name_and_description:str...]',
                    aliases=[])  # TODO: level
    def command_update(self, event, invite, category_channel=None, name_and_description=""):
        if event.msg.channel.id not in self.config.addChannelIDs:
            return

        self.client.api.channels_typing(event.msg.channel.id)

        name = name_and_description.strip()
        description = ""
        if "|" in name:
            parts = name.split('|', 2)
            name = parts[0].strip()
            description = parts[1].strip()

        if len(name) > 32:
            event.msg.reply('name too long')
            return

        if len(description) > 100:
            event.msg.reply('description too long')
            return

        invite_code = extract_invite_code(invite)
        if len(invite_code) <= 0:
            event.msg.reply('no invite code found')
            return

        invite = self.client.api.invites_get(invite_code)

        if not is_valid_invite(self.client, invite, event.msg.author.id):
            event.msg.reply('invalid invite code')
            return

        discord_servers_found = orm.select(ds for ds in self.db.DiscordServer if ds.server_id == invite.guild.id)
        if discord_servers_found.count() <= 0:
            event.msg.reply('server not found in queue or index')
            return

        if category_channel is not None and not isinstance(category_channel, DiscoChannel):
            category_channel = self.state.channels.get(category_channel)

        if category_channel is not None and category_channel.guild_id != event.msg.channel.guild_id:
            event.msg.reply('invalid category channel')
            return

        genre_category_name = ""
        if category_channel is not None and category_channel.parent is not None:
            genre_category_name = category_channel.parent.name

        # TODO: add exception for staff
        if discord_servers_found.first().invitee_id != event.msg.author.id:
            event.msg.reply('you can only edit entries your submitted yourself')
            return

        attr = {'invite_code': invite.code}
        if len(name) > 0:
            attr['name'] = name
            attr['description'] = description
        if category_channel is not None and len(category_channel.name) > 0:
            attr['category_channel_name'] = category_channel.name
            attr['genre_category_name'] = genre_category_name

        update_discord_server(discord_servers_found.first(), attr)

        event.msg.reply('Updated!')
