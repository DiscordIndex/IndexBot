from disco.api.http import APIException


def send_approval_message(plugin, entry):
    # TODO: add emojis?
    message = '**Congratulations! Your submission has been added.**\n'
    message += 'You can now find `{entry.name}` (invite: discord.gg/{entry.invite_code}) in the server index.\n'.format(
        entry=entry)
    message += 'Thank you very much for submitting your server.'

    send_invitee_dm(plugin, entry, message)


def send_rejection_message(plugin, entry, moderator_user_id, reason):
    # TODO: add emojis?
    message = '**We are sorry to tell you we had to deny your server submission.**\n'
    message += 'The Server `{entry.name}` (invite: discord.gg/{entry.invite_code}) has been denied.\n'.format(
        entry=entry)
    message += 'Reason: `{reason}`. Responsible moderator: <@{moderator_user_id}>.\n'.format(reason=reason,
                                                                                             moderator_user_id=moderator_user_id)
    message += 'Feel free to resubmit your server if you have fixed the issue.\n'
    message += 'Please contact the moderator mentioned above in case of questions.'

    send_invitee_dm(plugin, entry, message)


def send_expiration_message(plugin, entry):
    # TODO: add emojis?
    message = '**Action required! Your server invite is expired.**\n'
    message += 'The invite for the server `{entry.name}` is expired.\n'.format(
        entry=entry)
    message += 'If you are still interested in having your server in the index,\n'
    message += 'please update the invite using the following command in <#{add_channel_ids[0]}>:\n'.format(
        add_channel_ids=plugin.config.addChannelIDs)
    message += '`@{botuser.username}#{botuser.discriminator} update <new invite link>`\n'.format(
        botuser=plugin.client.state.me)
    message += '(for example `@{botuser.username}#{botuser.discriminator} update discord.gg/abcxyz`)\n'.format(
        botuser=plugin.client.state.me)
    message += 'Your server has been hidden from the index until you update the invite.\n'
    message += 'If you are not interested in the listing anymore you can ignore this message.\n'

    send_invitee_dm(plugin, entry, message)


def send_invitee_dm(plugin, entry, message):
    try:
        dm_channel = plugin.client.api.users_me_dms_create(entry.invitee_id)
        dm_channel.send_message(message)
    except APIException:
        pass
