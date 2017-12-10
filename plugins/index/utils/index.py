import datetime

from pony import orm


@orm.db_session
def add_discord_server_to_queue(db, invite_code, server_id, server_name, server_description, invitee_id,
                                category_channel_name):
    db.DiscordServer(state=1,
                     invite_code=invite_code,
                     server_id=server_id,
                     name=server_name,
                     description=server_description,
                     invitee_id=invitee_id,
                     submitted_at=datetime.datetime.now(),
                     category_channel_name=category_channel_name,
                     # index_message_id=789,
                     last_checked=datetime.datetime.now())
    orm.commit()

    # TODO: queue logic
    # TODO: logging logic


@orm.db_session
def remove_discord_server(discord_server):
    discord_server.delete()
    orm.commit()

    # TODO: queue logic
    # TODO: index logic
    # TODO: logging logic


@orm.db_session
def update_discord_server(discord_server, attr=None):
    if attr is None:
        attr = {}

    discord_server.set(**attr)
    orm.commit()

    # TODO: queue logic
    # TODO: index logic
    # TODO: logging logic
