import uuid

from disco.types.message import MessageEmbed
from pony import orm

APPROVE_EMOJI = "✅"
DENY_EMOJI = "❌"


def get_queue_bot_message(plugin):
    # TODO: cache message
    for message in plugin.client.api.channels_messages_list(plugin.config.approvalQueueChannelID):
        if message.author.id == plugin.client.state.me.id and len(message.embeds) > 0:
            return message

    return None


def get_queue_embed_none():
    embed = MessageEmbed()
    embed.title = "Currently nothing queued."
    embed.set_footer(text="")
    # embed.color = 0xffd700
    return embed


def get_queue_embed_item(entry, count):
    description = entry.description
    if not description:
        description = "_None_"
    category_breadcrumbs = entry.category_channel_name
    if entry.genre_category_name:
        category_breadcrumbs = entry.genre_category_name + " / " + category_breadcrumbs

    embed = MessageEmbed()
    embed.title = "Items in queue: {numberOfItems}".format(numberOfItems=count)
    embed.add_field(name='Name', value=entry.name, inline=True)
    embed.add_field(name='Description', value=description, inline=True)
    embed.add_field(name='Invite', value="discord.gg/{entry.invite_code}".format(entry=entry), inline=True)
    embed.add_field(name='Server ID', value="`#{entry.server_id}`".format(entry=entry), inline=True)
    embed.add_field(name='Invitee', value="<@{entry.invitee_id}>\n`#{entry.invitee_id}`".format(entry=entry),
                    inline=True)
    embed.add_field(name='Submitted At', value="{entry.submitted_at}".format(entry=entry),
                    inline=True)
    embed.set_footer(text="ID: {entry.id}".format(entry=entry))
    # embed.color = 0xffd700
    return embed


def get_entry_from_embed(plugin, embed):
    if not embed.footer or not embed.footer.text:
        return None

    if not embed.footer.text.startswith("ID: "):
        return None

    entryId = uuid.UUID(embed.footer.text.replace("ID: ", "", 1).strip())

    discord_servers_found = orm.select(ds for ds in plugin.db.DiscordServer if ds.id == entryId)

    if discord_servers_found.count() <= 0:
        return None

    return discord_servers_found.first()


@orm.db_session
def update_approval_queue(plugin):
    discord_servers_found = orm.select(ds for ds in plugin.db.DiscordServer if ds.state == 1)

    bot_queue_message = get_queue_bot_message(plugin)

    # there are currently no items in queue
    if discord_servers_found.count() <= 0:
        # create message if there is no previous queue message
        if bot_queue_message is None:
            plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                       embed=get_queue_embed_none())
        # update message if there is a previous queue message
        else:
            edited_message = plugin.client.api.channels_messages_modify(plugin.config.approvalQueueChannelID,
                                                                        bot_queue_message.id,
                                                                        content="\u200B",
                                                                        embed=get_queue_embed_none())
            plugin.client.api.channels_messages_reactions_delete(edited_message.channel.id, edited_message.id,
                                                                 APPROVE_EMOJI)
            plugin.client.api.channels_messages_reactions_delete(edited_message.channel.id, edited_message.id,
                                                                 DENY_EMOJI)
    # there are items in the queu
    else:
        # create message if there is no previous queue message
        if bot_queue_message is None:
            new_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                     content="discord.gg/{entry.invite_code}".format(
                                                                         entry=discord_servers_found.first()),
                                                                     embed=get_queue_embed_item(
                                                                         discord_servers_found.first(),
                                                                         discord_servers_found.count()))
            plugin.client.api.channels_messages_reactions_create(new_message.channel.id, new_message.id, APPROVE_EMOJI)
            plugin.client.api.channels_messages_reactions_create(new_message.channel.id, new_message.id, DENY_EMOJI)
        else:
            entry = get_entry_from_embed(plugin, bot_queue_message.embeds[0])
            # remove and create if previous queue message was about an item not in the queue anymore or empty queue
            if entry is None or entry.state != 1:
                plugin.client.api.channels_messages_delete(plugin.config.approvalQueueChannelID, bot_queue_message.id)
                new_message = plugin.client.api.channels_messages_create(plugin.config.approvalQueueChannelID,
                                                                         content="discord.gg/{entry.invite_code}".format(
                                                                             entry=discord_servers_found.first()),
                                                                         embed=get_queue_embed_item(
                                                                             discord_servers_found.first(),
                                                                             discord_servers_found.count()))
                plugin.client.api.channels_messages_reactions_create(new_message.channel.id, new_message.id,
                                                                     APPROVE_EMOJI)
                plugin.client.api.channels_messages_reactions_create(new_message.channel.id, new_message.id, DENY_EMOJI)
            else:
                # refresh embed if previous queue message was about an item in the queue (to update counter and stuff)
                edited_message = plugin.client.api.channels_messages_modify(plugin.config.approvalQueueChannelID,
                                                                            bot_queue_message.id,
                                                                            content="discord.gg/{entry.invite_code}".format(
                                                                                entry=entry),
                                                                            embed=get_queue_embed_item(entry,
                                                                                                       discord_servers_found.count()))
                plugin.client.api.channels_messages_reactions_create(edited_message.channel.id, edited_message.id,
                                                                     APPROVE_EMOJI)
                plugin.client.api.channels_messages_reactions_create(edited_message.channel.id, edited_message.id,
                                                                     DENY_EMOJI)
    return
