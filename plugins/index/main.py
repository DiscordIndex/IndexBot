import datetime
import time
from threading import Thread

from disco.api.http import APIException
from disco.bot import Plugin
from disco.types.channel import Channel as DiscoChannel
from pony import orm

from db import DbHandler
from plugins.index.utils.discordindex import update_discord_index, get_channel_for_name_and_category
from plugins.index.utils.discordindex_refresh import start_discordindex_refresh_loop
from plugins.index.utils.index import add_discord_server_to_queue, remove_discord_server, update_discord_server
from plugins.index.utils.invite import extract_invite_code, is_valid_invite
from plugins.index.utils.permissions import is_mod
from plugins.index.utils.query_response_manager import QueryResponseManager
from plugins.index.utils.queue import update_approval_queue, DENY_EMOJI, get_queue_bot_message, get_entry_from_embed, \
    reject_queue_entry, APPROVE_EMOJI, approve_queue_entry, EDIT_EMOJI
from plugins.index.utils.servers_healthcheck import start_servers_healthcheck, start_servers_healthcheck_loop
from .config import IndexPluginConfig


def is_queue_approve_reaction(event):
    if event.emoji.name == APPROVE_EMOJI:
        return True
    return False


def is_queue_edit_reaction(event):
    if event.emoji.name == EDIT_EMOJI:
        return True
    return False


def is_queue_reject_reaction(event):
    if event.emoji.name == DENY_EMOJI:
        return True
    return False


def deny_reason_callback(plugin=None, user_id=0, text="", more_args=None):
    reject_queue_entry(plugin, more_args['entry'], user_id, text)
    plugin.log.info(
        '#{author_id} rejected '
        'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
        'name: {entry[name]} description: {entry[description]} '
        'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
        'invitee: #{entry[invitee_id]} '
        'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]} '
        'reason: {reason}'.format(
            author_id=user_id,
            entry=more_args['entry'].to_dict(), reason=text))


def query_edit_callback(plugin=None, user_id=0, text="", more_args=None):
    plugin.client.api.channels_typing(plugin.config.approvalQueueChannelID)
    sent_message = None
    text = text.strip()
    if text.lower().startswith('name'):
        new_value_text = text[4:].strip()
        if len(new_value_text) < 1:
            sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                      '<@{user_id}> name too short'.format(
                                                                          user_id=user_id))
        elif len(new_value_text) > 32:
            sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                      '<@{user_id}> name too long'.format(
                                                                          user_id=user_id))
        else:
            update_discord_server(plugin, more_args['entry'], {'name': new_value_text})
            sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                      '<@{user_id}> done, changed name!'.format(
                                                                          user_id=user_id))
            plugin.log.info(
                '#{author_id} edited '
                'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
                'name: {entry[name]} description: {entry[description]} '
                'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
                'invitee: #{entry[invitee_id]} '
                'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]} '
                'new name: {new_value}'.format(
                    author_id=user_id,
                    entry=more_args['entry'].to_dict(), new_value=new_value_text))
    elif text.lower().startswith('description'):
        new_value_text = text[11:].strip()
        if len(new_value_text) > 100:
            sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                      '<@{user_id}> description too long'.format(
                                                                          user_id=user_id))
        else:
            update_discord_server(plugin, more_args['entry'], {'description': new_value_text})
            sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                      '<@{user_id}> done, changed description!'.format(
                                                                          user_id=user_id))
            plugin.log.info(
                '#{author_id} edited '
                'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
                'name: {entry[name]} description: {entry[description]} '
                'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
                'invitee: #{entry[invitee_id]} '
                'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]} '
                'new description: {new_value}'.format(
                    author_id=user_id,
                    entry=more_args['entry'].to_dict(), new_value=new_value_text))
    elif text.lower().startswith('category'):
        new_value_text = text[8:].strip()
        if new_value_text.lower().startswith('<#') and new_value_text.lower().endswith('>'):
            new_value_text = new_value_text.replace('<#', '', 1)
            new_value_text = new_value_text.replace('>', '', 1)

        queue_channel = plugin.state.channels.get(plugin.config.approvalQueueChannelID)
        category_channel = plugin.state.channels.get(int(new_value_text))

        if not category_channel or (
                category_channel and category_channel.guild_id != queue_channel.guild_id):
            sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                      '<@{user_id}> invalid channel.'.format(
                                                                          user_id=user_id))
        else:
            genre_category_name = ""
            if category_channel.parent is not None:
                genre_category_name = category_channel.parent.name
            update_discord_server(plugin, more_args['entry'], {'category_channel_name': category_channel.name,
                                                               'genre_category_name': genre_category_name})
            sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                      '<@{user_id}> done, changed category!'.format(
                                                                          user_id=user_id))
            plugin.log.info(
                '#{author_id} edited '
                'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
                'name: {entry[name]} description: {entry[description]} '
                'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
                'invitee: #{entry[invitee_id]} '
                'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]} '
                'new category_channel_name: {category_channel_name} new genre_category_name: {genre_category_name}'.format(
                    author_id=user_id,
                    entry=more_args['entry'].to_dict(), category_channel_name=category_channel.name,
                    genre_category_name=genre_category_name))
    else:
        sent_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                  '<@{user_id}> invalid response'.format(
                                                                      user_id=user_id))

    if sent_message:
        thread = Thread(target=cleanup_message, args=(plugin, plugin.config.approvalQueueChannelID, sent_message.id))
        thread.start()


def cleanup_message(plugin, channel_id, message_id, delay=10):
    time.sleep(delay)
    try:
        plugin.client.api.channels_messages_delete(channel_id, message_id)
    except APIException:
        pass


@Plugin.with_config(IndexPluginConfig)
class IndexPlugin(Plugin):
    def __init__(self, bot, config):
        super().__init__(bot, config)
        self.db = DbHandler().getDb()
        self.denyReasonQueryResponseManager = QueryResponseManager(deny_reason_callback)
        self.queueEditQueryResponseManager = QueryResponseManager(query_edit_callback)
        start_servers_healthcheck_loop(self)
        start_discordindex_refresh_loop(self)
        self.cached_queue_message = None

    def load(self, ctx):
        super(IndexPlugin, self).load(ctx)

    @Plugin.command('ping')
    def command_ping(self, event):
        start = datetime.datetime.now()
        message = event.msg.reply('pong')
        end = datetime.datetime.now()
        message.edit('pong (edit took {time:.0f} ms)'.format(time=(end - start).total_seconds() * 1000))

    @Plugin.command('refresh queue')
    def command_refresh_queue(self, event):
        if event.msg.channel.guild_id != self.config.indexGuildID:
            return

        if not is_mod(self, event.msg.author.id):
            return
        self.client.api.channels_typing(event.msg.channel.id)
        update_approval_queue(self)
        event.msg.reply('Refreshed queue')

    @Plugin.command('refresh index')
    def command_refresh_index(self, event):
        if event.msg.channel.guild_id != self.config.indexGuildID:
            return

        if not is_mod(self, event.msg.author.id):
            return
        self.client.api.channels_typing(event.msg.channel.id)
        update_discord_index(self)
        event.msg.reply('Refreshed index')

    @Plugin.command('healthcheck')
    def command_healthcheck(self, event):
        if event.msg.channel.guild_id != self.config.indexGuildID:
            return

        if not is_mod(self, event.msg.author.id):
            return
        self.client.api.channels_typing(event.msg.channel.id)
        start_servers_healthcheck(self)
        event.msg.reply('Completed healthcheck')

    @orm.db_session
    @Plugin.command('add',
                    '<invite:str> <category_channel:channel|snowflake> <name_and_description:str...>',
                    aliases=['submit', 'sudo-add'])
    def command_add(self, event, invite, category_channel, name_and_description):
        if event.msg.channel.guild_id != self.config.indexGuildID:
            return

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

        if self.db.DiscordServer.get(server_id=invite.guild.id):
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

        if not get_channel_for_name_and_category(self, category_channel.name, genre_category_name):
            event.msg.reply('invalid category channel')
            return

        add_discord_server_to_queue(self, invite_code, invite.guild.id, name, description, invite.inviter.id,
                                    category_channel.name, genre_category_name)
        self.log.info(
            '{author.username} #{author.id} added '
            'server to queue: {invite.guild.name} #{invite.guild.id} discord.gg/{invite_code} '
            'name: {name} description: {description} '
            'category: {category_channel_name} genre: {genre_category_name} '
            'invitee: {invite.inviter.username} #{invite.inviter.id} '
            'sudo: {sudo}'.format(
                author=event.msg.author,
                invite=invite, invite_code=invite_code, category_channel_name=category_channel.name,
                genre_category_name=genre_category_name, name=name, description=description, sudo=sudo))

        event.msg.reply('Added to queue!')

    @orm.db_session
    @Plugin.command('remove',
                    '<invite:str>',
                    aliases=['delete', 'withdraw', 'sudo-remove'])
    def command_remove(self, event, invite):
        if event.msg.channel.guild_id != self.config.indexGuildID:
            return

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

        discord_server_found = self.db.DiscordServer.get(invite_code=invite_code)
        if not discord_server_found:
            event.msg.reply('invite not found in queue or index')
            return

        if discord_server_found.invitee_id != event.msg.author.id and sudo == False:
            event.msg.reply('you can only remove entries your submitted yourself')
            return

        discord_server_found_data = discord_server_found.to_dict()
        remove_discord_server(self, discord_server_found, event.msg.author.id)
        self.log.info(
            '{author.username} #{author.id} removed '
            'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
            'name: {entry[name]} description: {entry[description]} '
            'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
            'invitee: #{entry[invitee_id]} '
            'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]} '
            'index message id: {entry[index_message_id]} '
            'sudo: {sudo}'.format(
                author=event.msg.author,
                entry=discord_server_found_data, sudo=sudo))

        event.msg.reply('Removed!')

    @orm.db_session
    @Plugin.command('update',
                    '<invite:str> [category_channel:channel|snowflake] [name_and_description:str...]',
                    aliases=['sudo-update'])
    def command_update(self, event, invite, category_channel=None, name_and_description=""):
        if event.msg.channel.guild_id != self.config.indexGuildID:
            return

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

        discord_server_found = self.db.DiscordServer.get(server_id=invite.guild.id)
        if not discord_server_found:
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

        if not get_channel_for_name_and_category(self, category_channel.name, genre_category_name):
            event.msg.reply('invalid category channel')
            return

        if discord_server_found.invitee_id != event.msg.author.id and sudo == False:
            event.msg.reply('you can only edit entries your submitted yourself')
            return

        attr = {'invite_code': invite.code}
        response_text = 'Updated!'
        if len(name) > 0:
            attr['name'] = name
            attr['description'] = description
        if category_channel is not None and len(category_channel.name) > 0:
            if category_channel.name != discord_server_found.category_channel_name or genre_category_name != discord_server_found.genre_category_name:
                attr['category_channel_name'] = category_channel.name
                attr['genre_category_name'] = genre_category_name
                if not sudo:
                    attr['state'] = 4
                    response_text = 'Category changes have to be approved, we will inform you when it\'s done!'

        before_data = discord_server_found.to_dict()
        update_discord_server(self, discord_server_found, attr)
        self.log.info(
            '{author.username} #{author.id} updated '
            'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
            'name: {entry[name]} description: {entry[description]} '
            'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
            'invitee: #{entry[invitee_id]} '
            'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]} '
            'index message id: {entry[index_message_id]} '
            'sudo: {sudo} '
            'new data: {attr}'.format(
                author=event.msg.author,
                entry=before_data, sudo=sudo, attr=attr))

        event.msg.reply(response_text)

    @Plugin.listen('MessageReactionAdd', conditional=is_queue_approve_reaction)
    def on_queue_approval_reaction(self, event):
        if event.channel.guild_id != self.config.indexGuildID:
            return

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
        self.log.info(
            '#{author_id} approved '
            'server: #{entry[server_id]} discord.gg/{entry[invite_code]} '
            'name: {entry[name]} description: {entry[description]} '
            'category: {entry[category_channel_name]} genre: {entry[genre_category_name]} '
            'invitee: #{entry[invitee_id]} '
            'submitted at: {entry[submitted_at]} last checked: {entry[submitted_at]}'.format(
                author_id=event.user_id,
                entry=entry.to_dict()))

        try:
            self.client.api.channels_messages_reactions_delete(event.channel_id, event.message_id, event.emoji.name,
                                                               event.user_id)
        except APIException:
            pass

    @Plugin.listen('MessageReactionAdd', conditional=is_queue_reject_reaction)
    def on_queue_reject_reaction(self, event):
        if event.channel.guild_id != self.config.indexGuildID:
            return

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

        deny_query_text = '<@{user.id}>\n' \
                          'Please tell me the reason for rejecting `{entry.name}`.\n' \
                          'Say `cancel` to cancel rejecting the server.'.format(
            user=user,
            entry=entry)

        self.denyReasonQueryResponseManager.start_query(self, user.id, event.channel_id, deny_query_text,
                                                        more_args={'entry': entry})

        try:
            self.client.api.channels_messages_reactions_delete(event.channel_id, event.message_id, event.emoji.name,
                                                               event.user_id)
        except APIException:
            pass

    @Plugin.listen('MessageReactionAdd', conditional=is_queue_edit_reaction)
    def on_queue_edit_reaction(self, event):
        if event.channel.guild_id != self.config.indexGuildID:
            return

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

        edit_query_text = '<@{user.id}>\n' \
                          'Please tell me what change you would like to make for `{entry.name}`.\n' \
                          'Say `name <New Name>` to change the name.\n' \
                          'Example `name Kpop Server Index`.\n' \
                          'Say `description <New Description>` to change the description.\n' \
                          'Example `description The server for all Kpop groups.`.\n' \
                          'Say `category <#new-category>` to change the category.\n' \
                          'Example `category #general`.\n' \
                          'Say `cancel` to cancel editing the server.\n'.format(
            user=user,
            entry=entry)

        self.queueEditQueryResponseManager.start_query(self, user.id, event.channel_id, edit_query_text,
                                                       more_args={'entry': entry})

        try:
            self.client.api.channels_messages_reactions_delete(event.channel_id, event.message_id, event.emoji.name,
                                                               event.user_id)
        except APIException:
            pass

    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        if event.message.channel.guild_id != self.config.indexGuildID:
            return

        if event.message.channel.id != self.config.approvalQueueChannelID:
            return

        if not is_mod(self, event.message.author.id):
            return

        self.denyReasonQueryResponseManager.handle_possible_response(self, event.message)
        self.queueEditQueryResponseManager.handle_possible_response(self, event.message)
