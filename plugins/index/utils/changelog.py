from disco.types.message import MessageEmbed


def changelog_post_approval(plugin, entry, mod_user_id):
    description = entry.description
    if not description:
        description = '_None_'
    category_breadcrumbs = '#' + entry.category_channel_name
    if entry.genre_category_name:
        category_breadcrumbs = '#' + entry.genre_category_name + ' / ' + category_breadcrumbs

    embed = MessageEmbed()
    embed.title = '✅ Server has been approved!'
    embed.add_field(name='🏷 Name', value=entry.name, inline=True)
    embed.add_field(name='📖 Description', value=description, inline=True)
    embed.add_field(name='🗃 Category', value=category_breadcrumbs, inline=True)
    embed.add_field(name='🚩 Invite', value='https://discord.gg/{entry.invite_code}'.format(entry=entry), inline=True)
    embed.add_field(name='👤 Invitee', value='<@{entry.invitee_id}>'.format(entry=entry),
                    inline=True)
    embed.add_field(name='📆 Submitted At', value='{entry.submitted_at}'.format(entry=entry),
                    inline=True)
    embed.add_field(name='👮 Moderator', value='<@{mod_user_id}>'.format(mod_user_id=mod_user_id),
                    inline=True)
    embed.set_footer(text='ID: {entry.id}'.format(entry=entry))

    for channel_id in plugin.config.changelogChannelIDs:
        plugin.client.api.channels_messages_create(channel_id, embed=embed)


def changelog_post_rejection(plugin, entry, mod_user_id, reason):
    description = entry.description
    if not description:
        description = '_None_'
    category_breadcrumbs = '#' + entry.category_channel_name
    if entry.genre_category_name:
        category_breadcrumbs = '#' + entry.genre_category_name + ' / ' + category_breadcrumbs

    embed = MessageEmbed()
    embed.title = '❌ Server has been rejected!'
    embed.add_field(name='🏷 Name', value=entry.name, inline=True)
    embed.add_field(name='📖 Description', value=description, inline=True)
    embed.add_field(name='🗃 Category', value=category_breadcrumbs, inline=True)
    embed.add_field(name='❓ Reason', value=reason, inline=True)
    embed.add_field(name='👤 Invitee', value='<@{entry.invitee_id}>'.format(entry=entry),
                    inline=True)
    embed.add_field(name='📆 Submitted At', value='{entry.submitted_at}'.format(entry=entry),
                    inline=True)
    embed.add_field(name='👮 Moderator', value='<@{mod_user_id}>'.format(mod_user_id=mod_user_id),
                    inline=True)
    embed.set_footer(text='ID: {entry.id}'.format(entry=entry))

    for channel_id in plugin.config.changelogChannelIDs:
        plugin.client.api.channels_messages_create(channel_id, embed=embed)


def changelog_post_removal(plugin, entry_data, author_user_id, reason):
    # don't post above withdrawals from the queue
    if entry_data['state'] == 1:
        return

    description = entry_data['description']
    if not description:
        description = '_None_'
    category_breadcrumbs = '#' + entry_data['category_channel_name']
    if entry_data['genre_category_name']:
        category_breadcrumbs = '#' + entry_data['genre_category_name'] + ' / ' + category_breadcrumbs

    embed = MessageEmbed()
    embed.title = '🚮 Server has been removed!'
    embed.add_field(name='🏷 Name', value=entry_data['name'], inline=True)
    embed.add_field(name='📖 Description', value=description, inline=True)
    embed.add_field(name='🗃 Category', value=category_breadcrumbs, inline=True)
    if reason != "":
        embed.add_field(name='❓ Reason', value=reason, inline=True)
    embed.add_field(name='👤 Invitee', value='<@{entry[invitee_id]}>'.format(entry=entry_data),
                    inline=True)
    if entry_data['invitee_id'] != author_user_id:
        embed.add_field(name='👮 Moderator', value='<@{author_user_id}>'.format(author_user_id=author_user_id),
                        inline=True)
    embed.set_footer(text='ID: {entry[id]}'.format(entry=entry_data))

    for channel_id in plugin.config.changelogChannelIDs:
        plugin.client.api.channels_messages_create(channel_id, embed=embed)


def changelog_post_update(plugin, before_data, after_data):
    # don't post above withdrawals from the queue
    if after_data['state'] == 1:
        return

    name = after_data['name']
    if before_data['name'] != after_data['name']:
        name = before_data['name'] + " ➡ " + name

    description = after_data['description']
    if not description:
        description = '_None_'
    if before_data['description'] != after_data['description']:
        before_description = before_data['description']
        if not before_description:
            before_description = '_None_'
        description = before_description + " ➡ " + description

    category_breadcrumbs = '#' + after_data['category_channel_name']
    if after_data['genre_category_name']:
        category_breadcrumbs = '#' + after_data['genre_category_name'] + ' / ' + category_breadcrumbs
    if before_data['category_channel_name'] != after_data['category_channel_name'] or before_data[
        'genre_category_name'] != after_data['genre_category_name']:
        before_category_breadcrumbs = '#' + before_data['category_channel_name']
        if before_data['genre_category_name']:
            before_category_breadcrumbs = '#' + before_data['genre_category_name'] + ' / ' + before_category_breadcrumbs
        category_breadcrumbs = before_category_breadcrumbs + " ➡ " + category_breadcrumbs

    invite = 'https://discord.gg/' + after_data['invite_code']
    if before_data['invite_code'] != after_data['invite_code']:
        invite = 'https://discord.gg/' + before_data['invite_code'] + " ➡ " + invite

    embed = MessageEmbed()
    embed.title = '🔄 Server has been updated!'
    embed.add_field(name='🏷 Name', value=name, inline=True)
    embed.add_field(name='📖 Description', value=description, inline=True)
    embed.add_field(name='🗃 Category', value=category_breadcrumbs, inline=True)
    embed.add_field(name='🚩 Invite', value=invite, inline=True)
    embed.add_field(name='👤 Invitee', value='<@{entry[invitee_id]}>'.format(entry=after_data),
                    inline=True)
    embed.set_footer(text='ID: {entry[id]}'.format(entry=after_data))

    for channel_id in plugin.config.changelogChannelIDs:
        plugin.client.api.channels_messages_create(channel_id, embed=embed)
