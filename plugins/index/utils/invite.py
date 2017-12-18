import re


def extract_invite_code(invite_link):
    invite_link = invite_link.strip()

    invite_code_regex = re.compile('^([a-z0-9]+)$', re.IGNORECASE)

    if invite_code_regex.match(invite_link):
        return invite_link

    invite_regex = re.compile('(http(s)?:\/\/)?(discord\.gg|discordapp\.com\/invite)\/([a-z0-9]+)', re.IGNORECASE)

    parts = invite_regex.findall(invite_link)

    if len(parts) < 1 or len(parts[0]) < 4:
        return ""

    return parts[0][3]


def is_valid_invite(client, invite, submitter_id, discord_server_entry=None):
    # TODO: add exception for staff

    if invite.inviter.id != submitter_id:
        return False

    if discord_server_entry:
        if invite.guild.id != discord_server_entry.server_id:
            return False

    return True
