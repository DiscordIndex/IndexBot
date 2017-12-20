from disco.api.http import APIException


def send_approval_message(plugin, entry):
    message = ':white_check_mark: **Congratulations! Your submission has been added.**\n' \
              'You can now find `{entry.name}` (invite: discord.gg/{entry.invite_code}) in the server index.\n' \
              'Thank you very much for submitting your server.'.format(
        entry=entry)

    send_invitee_dm(plugin, entry, message)


def send_rejection_message(plugin, entry, moderator_user_id, reason):
    message = ':x: **We are sorry to tell you we had to deny your server submission.**\n' \
              'The Server `{entry.name}` (invite: discord.gg/{entry.invite_code}) has been denied.\n' \
              'Reason: `{reason}`. Responsible moderator: <@{moderator_user_id}>.\n' \
              'Feel free to resubmit your server if you have fixed the issue.\n' \
              'Please contact the moderator mentioned above in case of questions.'.format(
        entry=entry, reason=reason, moderator_user_id=moderator_user_id)

    send_invitee_dm(plugin, entry, message)


def send_expiration_message(plugin, entry):
    message = ':warning: **Action required! Your server invite is expired.**\n' \
              'The invite for the server `{entry.name}` is expired.\n' \
              'If you are still interested in having your server in the index,\n' \
              'please update the invite using the following command in <#{add_channel_ids[0]}>:\n' \
              '`@{botuser.username}#{botuser.discriminator} update <new invite link>`\n' \
              '(for example `@{botuser.username}#{botuser.discriminator} update discord.gg/abcxyz`)\n' \
              'Your server has been hidden from the index until you update the invite.\n' \
              'If you are not interested in the listing anymore you can ignore this message.\n'.format(
        entry=entry, add_channel_ids=plugin.config.addChannelIDs, botuser=plugin.client.state.me)

    send_invitee_dm(plugin, entry, message)


def send_invitee_dm(plugin, entry, message):
    try:
        dm_channel = plugin.client.api.users_me_dms_create(entry.invitee_id)
        dm_channel.send_message(message)
    except APIException:
        pass
