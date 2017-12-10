from disco.bot import Plugin
from disco.types.channel import Channel as DiscoChannel
from pony import orm

from db import DbHandler
from plugins.index.utils.invite import extract_invite_code, is_valid_invite
from plugins.index.utils.queue import add_to_queue
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

        add_to_queue(self.db, invite_code, invite.guild.id, name, description, event.msg.author.id,
                     category_channel.name)

        event.msg.reply('Added to queue!')

    @Plugin.command('update', '<invite:str> [category:channel|snowflake] [name_and_description:str...]')  # TODO: level
    def command_update(self, event, invite, category=None, name_and_description=""):
        if event.msg.channel.id not in self.config.addChannelIDs:
            event.msg.reply('invalid channel')
            return

        if category is not None:
            if not isinstance(category, DiscoChannel):
                category = self.state.channels.get(category)

        name = name_and_description.strip()
        description = ""
        if "|" in name_and_description:
            parts = name_and_description.split('|', 2)
            name = parts[0].strip()
            description = parts[1].strip()

        event.msg.reply('Update\nInvite: {invite}\nCategory: <#{category}>\nName: {name}\nDescription: {description}'.
                        format(invite=invite, category=category.id, name=name, description=description))
