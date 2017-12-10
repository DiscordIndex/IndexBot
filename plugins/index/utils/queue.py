import datetime

from pony import orm


def add_to_queue(db, invite_code, server_id, server_name, server_description, invitee_id, category_channel_name):
    db.DiscordServer(state=1,
                     invite_code=invite_code,
                     server_id=server_id,
                     server_name=server_name,
                     description=server_description,
                     invitee_id=invitee_id,
                     submitted_at=datetime.datetime.now(),
                     category_channel_name=category_channel_name,
                     # index_message_id=789,
                     last_checked=datetime.datetime.now())
    orm.commit()

    # TODO: queue logic
