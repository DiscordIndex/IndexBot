import datetime
import uuid

from pony import orm


def define_discordserver(db):
    class DiscordServer(db.Entity):
        id = orm.PrimaryKey(uuid.UUID, default=uuid.uuid4())
        state = orm.Required(int, min=1, max=3)  # 1 = waiting for approval, 2 = public, 3 = expired
        invite_code = orm.Required(str, unique=True)
        server_id = orm.Required(int, unique=True, size=64)
        name = orm.Required(str, max_len=32)
        description = orm.Optional(str, max_len=100)
        invitee_id = orm.Required(int, size=64)
        submitted_at = orm.Required(datetime.datetime)
        category_channel_name = orm.Required(str)
        index_message_id = orm.Optional(int, size=64)
        last_checked = orm.Required(datetime.datetime)
