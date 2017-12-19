from disco.api.http import APIException
from disco.bot import Plugin
from disco.types.channel import Channel as DiscoChannel
from pony import orm

from db import DbHandler
from plugins.index.utils.index import add_discord_server_to_queue, remove_discord_server, update_discord_server
from plugins.index.utils.invite import extract_invite_code, is_valid_invite
from plugins.index.utils.permissions import is_mod
from plugins.index.utils.query_response_manager import QueryResponseManager
from plugins.index.utils.queue import update_approval_queue, DENY_EMOJI, get_queue_bot_message, get_entry_from_embed, \
    reject_queue_entry, APPROVE_EMOJI, approve_queue_entry
from plugins.index.utils.servers_healthcheck import start_servers_healthcheck, start_servers_healthcheck_loop
from .config import IndexPluginConfig


def is_queue_reject_reaction(event):
    if event.emoji.name == DENY_EMOJI:
        return True


def is_queue_approve_reaction(event):
    if event.emoji.name == APPROVE_EMOJI:
        return True


def deny_reason_callback(plugin=None, user_id=0, text="", more_args=None):
    reject_queue_entry(plugin, more_args['entry'], user_id, text)


@Plugin.with_config(IndexPluginConfig)
class IndexPlugin(Plugin):
    def __init__(self, bot, config):
        super().__init__(bot, config)
        self.db = DbHandler().getDb()
        self.denyReasonQueryResponseManager = QueryResponseManager(deny_reason_callback)
        start_servers_healthcheck_loop(self)
        self.cached_queue_message = None

    def load(self, ctx):
        super(IndexPlugin, self).load(ctx)

    @Plugin.command('ping')
    def command_ping(self, event):
        event.msg.reply('pong')

    @Plugin.command('channels')
    def command_channels(self, event):
        self.client.api.channels_typing(event.msg.channel.id)
        event.msg.reply('Add Channels: <#' + ">, <#".join(str(x) for x in self.config.addChannelIDs) + '>')

    @Plugin.command('refresh queue')
    def command_refresh_queue(self, event):
        self.client.api.channels_typing(event.msg.channel.id)
        update_approval_queue(self)
        event.msg.reply('Refreshed queue')

    @Plugin.command('healthcheck')
    def command_healthcheck(self, event):
        self.client.api.channels_typing(event.msg.channel.id)
        start_servers_healthcheck(self)
        event.msg.reply('Completed healthcheck')

    @orm.db_session
    @Plugin.command('add',
                    '<invite:str> <category_channel:channel|snowflake> <name_and_description:str...>',
                    aliases=['submit', 'sudo-add'])
    def command_add(self, event, invite, category_channel, name_and_description):
        if event.msg.channel.id not in self.config.addChannelIDs:
            return

        sudo = False
        if event.name == 'sudo-add':
            if not is_mod(self, event.msg.author.id):
                return
            sudo = True

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

        try:
            invite = self.client.api.invites_get(invite_code)
        except APIException:
            event.msg.reply('expired invite code')
            return

        if orm.select(
                orm.count(ds) for ds in self.db.DiscordServer if ds.server_id == invite.guild.id).first() > 0:
            event.msg.reply('server already in the index or queue')
            return

        if not is_valid_invite(self.client, invite, event.msg.author.id, sudo=sudo):
            event.msg.reply('you can only submit invites you generated yourself')
            return

        if not isinstance(category_channel, DiscoChannel):
            category_channel = self.state.channels.get(category_channel)

        if category_channel is None or category_channel.guild_id != event.msg.channel.guild_id:
            event.msg.reply('invalid category channel')
            return

        genre_category_name = ""
        if category_channel.parent is not None:
            genre_category_name = category_channel.parent.name

        add_discord_server_to_queue(self, invite_code, invite.guild.id, name, description, invite.inviter.id,
                                    category_channel.name, genre_category_name)

        event.msg.reply('Added to queue!')

    @orm.db_session
    @Plugin.command('remove',
                    '<invite:str>',
                    aliases=['delete', 'withdraw', 'sudo-remove'])
    def command_remove(self, event, invite):
        if event.msg.channel.id not in self.config.addChannelIDs:
            return

        sudo = False
        if event.name == 'sudo-remove':
            if not is_mod(self, event.msg.author.id):
                return
            sudo = True

        self.client.api.channels_typing(event.msg.channel.id)

        invite_code = extract_invite_code(invite)
        if len(invite_code) <= 0:
            event.msg.reply('no invite code found')
            return

        discord_servers_found = orm.select(ds for ds in self.db.DiscordServer if ds.invite_code == invite_code)
        if discord_servers_found.count() <= 0:
            event.msg.reply('invite not found in queue or index')
            return

        if discord_servers_found.first().invitee_id != event.msg.author.id and sudo == False:
            event.msg.reply('you can only remove entries your submitted yourself')
            return

        remove_discord_server(self, discord_servers_found.first(), event.msg.author.id)

        event.msg.reply('Removed!')

    @orm.db_session
    @Plugin.command('update',
                    '<invite:str> [category_channel:channel|snowflake] [name_and_description:str...]',
                    aliases=['sudo-update'])
    def command_update(self, event, invite, category_channel=None, name_and_description=""):
        if event.msg.channel.id not in self.config.addChannelIDs:
            return

        sudo = False
        if event.name == 'sudo-update':
            if not is_mod(self, event.msg.author.id):
                return
            sudo = True

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

        try:
            invite = self.client.api.invites_get(invite_code)
        except APIException:
            event.msg.reply('expired invite code')
            return

        if not is_valid_invite(self.client, invite, event.msg.author.id, sudo=sudo):
            event.msg.reply('you can only submit invites you generated yourself')
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

        if discord_servers_found.first().invitee_id != event.msg.author.id and sudo == False:
            event.msg.reply('you can only edit entries your submitted yourself')
            return

        attr = {'invite_code': invite.code}
        if len(name) > 0:
            attr['name'] = name
            attr['description'] = description
        if category_channel is not None and len(category_channel.name) > 0:
            attr['category_channel_name'] = category_channel.name
            attr['genre_category_name'] = genre_category_name

        update_discord_server(self, discord_servers_found.first(), attr)

        event.msg.reply('Updated!')

    @Plugin.listen('MessageReactionAdd', conditional=is_queue_reject_reaction)
    def on_queue_reject_reaction(self, event):
        if event.channel_id != self.config.approvalQueueChannelID:
            return

        if not is_mod(self, event.user_id):
            return

        bot_queue_message = get_queue_bot_message(self)

        if not bot_queue_message:
            return

        entry = get_entry_from_embed(self, bot_queue_message.embeds[0])

        if not entry:
            return

        user = self.client.state.users[event.user_id]

        if not user:
            return

        deny_query_text = "<@{user.id}>\nPlease tell me the reason for rejecting {entry.name}.\nUse `cancel` to cancel rejecting the server.".format(
            user=user,
            entry=entry)

        self.denyReasonQueryResponseManager.start_query(self, user.id, event.channel_id, deny_query_text,
                                                        more_args={'entry': entry})

        try:
            self.client.api.channels_messages_reactions_delete(event.channel_id, event.message_id, event.emoji.name,
                                                               event.user_id)
        except APIException:
            pass

    @Plugin.listen('MessageReactionAdd', conditional=is_queue_approve_reaction)
    def on_queue_approval_reaction(self, event):
        if event.channel_id != self.config.approvalQueueChannelID:
            return

        if not is_mod(self, event.user_id):
            return

        bot_queue_message = get_queue_bot_message(self)

        if not bot_queue_message:
            return

        entry = get_entry_from_embed(self, bot_queue_message.embeds[0])

        if not entry:
            return

        user = self.client.state.users[event.user_id]

        if not user:
            return

        approve_queue_entry(self, entry, event.user_id)

        try:
            self.client.api.channels_messages_reactions_delete(event.channel_id, event.message_id, event.emoji.name,
                                                               event.user_id)
        except APIException:
            pass

    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        if event.message.channel.id != self.config.approvalQueueChannelID:
            return

        if not is_mod(self, event.message.author.id):
            return

        self.denyReasonQueryResponseManager.handle_possible_response(self, event.message)
