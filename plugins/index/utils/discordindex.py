from disco.api.http import APIException
from disco.api.http import Routes
from pony import orm


@orm.db_session
def update_discord_index(plugin, only_in_channel_id=None):
    index_guild = plugin.client.state.guilds.get(plugin.config.indexGuildID)
    index_targets = {}

    only_in_channel = None
    if only_in_channel_id:
        only_in_channel = index_guild.channels.get(only_in_channel_id)
        parent_name = ""
        if only_in_channel.parent_id:
            parent_name = '#' + index_guild.channels.get(
                only_in_channel.parent_id).name + ' / '
        plugin.log.info(
            'discordindex: updating channel ' + parent_name + '#' + only_in_channel.name + ' (' + str(
                only_in_channel.id) + ')')
    else:
        plugin.log.info('discordindex: updating all channels')

    for discord_server in orm.select(ds for ds in plugin.db.DiscordServer if ds.state == 2):
        index_channel = get_channel_for_name_and_category(plugin, discord_server.category_channel_name,
                                                          discord_server.genre_category_name, guild=index_guild)
        if index_channel:
            if only_in_channel and index_channel.id != only_in_channel.id:
                # print('skipped #' + index_channel.name)
                continue
            if index_channel in index_targets:
                index_targets[index_channel].append(discord_server)
            else:
                index_targets[index_channel] = [discord_server]
        else:
            plugin.log.warn('no channel found for discord_server #' + discord_server.id)

    # print(index_targets)

    if only_in_channel:
        if only_in_channel not in index_targets:
            # delete unused channel messages
            index_target_channel_messages = plugin.client.api.channels_messages_list(
                only_in_channel.id,
                after=1,
                limit=100)
            # TODO: handle more than 100 messages, state?
            index_target_channel_messages_iter = iter(index_target_channel_messages)
            for leftover_message in index_target_channel_messages_iter:
                if leftover_message.author.id != plugin.state.me.id:
                    continue
                # delete all following messages
                try:
                    plugin.client.api.channels_messages_delete(only_in_channel.id,
                                                               leftover_message.id)
                except APIException:
                    pass

    for index_target_channel, index_target_discord_servers in index_targets.items():
        # print("#" + index_guild.channels.get(
        #    index_target_channel.parent_id).name + " / #" + index_target_channel.name)
        index_target_discord_servers.sort(
            key=lambda discord_server: discord_server_sort_key(discord_server))

        if index_target_channel.id in plugin.config.rankedByMemberChannelIDs:
            index_target_discord_servers.sort(
                key=lambda discord_server: discord_server_sort_bymember_key(plugin, discord_server), reverse=True)

        index_target_channel_messages = plugin.client.api.channels_messages_list(
            index_target_channel.id,
            after=1,
            limit=100)
        index_target_channel_messages.reverse()
        # TODO: handle more than 100 messages, state?
        index_target_channel_messages_iter = iter(index_target_channel_messages)

        for index_target_channel_discord_server in index_target_discord_servers:
            # print(index_target_channel_discord_server.name + " (" + cleanup_server_name_for_sorting(
            #    index_target_channel_discord_server.name) + ")")
            try:
                while True:
                    current_message = next(index_target_channel_messages_iter)
                    if current_message.author.id != plugin.state.me.id:
                        continue
                    break
            except StopIteration:
                current_message = None

            if current_message:
                # update
                if current_message.content != get_discord_server_message(
                        plugin, index_target_channel_discord_server, index_target_channel.id):
                    # edit message
                    plugin.client.api.channels_messages_modify(index_target_channel.id,
                                                               current_message.id,
                                                               get_discord_server_message(
                                                                   plugin, index_target_channel_discord_server,
                                                                   index_target_channel.id))
            else:
                # create
                plugin.client.api.channels_messages_create(index_target_channel.id,
                                                           get_discord_server_message(
                                                               plugin, index_target_channel_discord_server,
                                                               index_target_channel.id))

        for leftover_message in index_target_channel_messages_iter:
            if leftover_message.author.id != plugin.state.me.id:
                continue
            # delete all following messages
            try:
                plugin.client.api.channels_messages_delete(index_target_channel.id,
                                                           leftover_message.id)
            except APIException:
                pass


def get_channel_for_name_and_category(plugin, channel_name, category_name, guild=None):
    if not guild:
        guild = plugin.client.state.guilds.get(plugin.config.indexGuildID)

    for _, index_channel in guild.channels.items():
        if index_channel.parent_id:
            if category_name.lower() != guild.channels.get(
                    index_channel.parent_id).name.lower():
                continue
        else:
            if category_name:
                continue
        if channel_name.lower() != index_channel.name.lower():
            continue
        if index_channel.id in plugin.config.addChannelIDs:
            continue
        if index_channel.id in plugin.config.changelogChannelIDs:
            continue
        if index_channel.id == plugin.config.approvalQueueChannelID:
            continue
        return index_channel
    return None


def discord_server_sort_key(discord_server):
    name = discord_server.name.lower()
    if name.startswith('the '):
        name = name[4:]
    if name.startswith('a '):
        name = name[2:]
    name = ''.join(e for e in name if e.isalnum())
    name = name.strip()
    name += str(discord_server.submitted_at.timestamp())
    # cleaned name + timestamp
    return name


def discord_server_sort_bymember_key(plugin, discord_server):
    target_guild = plugin.state.guilds.get(discord_server.server_id)
    if target_guild:
        return target_guild.member_count

    try:
        route = list(Routes.INVITES_GET)
        route[1] += '?with_counts=true'
        result = plugin.client.api.http(tuple(route),
                                        dict(invite=discord_server.invite_code))
    except APIException:
        return 1

    try:
        return int(result.json()['approximate_member_count'])
    except TypeError:
        return 1


def get_discord_server_message(plugin, discord_server, target_channel_id):
    result = '**{discord_server.name}** https://discord.gg/{discord_server.invite_code}\n' \
             '{discord_server.description}'.format(
        discord_server=discord_server).strip()
    # result += ' (sort key: ' + str(discord_server_sort_key(discord_server)) + ')'
    # result += ' (by member sort key: ' + str(discord_server_sort_bymember_key(plugin, discord_server)) + ')'
    if target_channel_id in plugin.config.emojiChannelIDs:
        target_guild = plugin.client.state.guilds.get(discord_server.server_id)
        if target_guild:
            if target_guild.emojis and len(target_guild.emojis) > 0:
                result += '\n'
                for emoji in target_guild.emojis.values():
                    result += emoji.__str__()
                result += ' ({emoji_count})'.format(emoji_count=len(target_guild.emojis))
        else:
            result += '\nIf this is your server please invite the Index Bot to see the server emoji listed here.'
    return result
