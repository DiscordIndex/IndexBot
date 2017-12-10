import datetime
import uuid

from pony import orm


def define_discordserver(db):
    class DiscordServer(db.Entity):
        id = orm.PrimaryKey(uuid.UUID, default=uuid.uuid4)
        state = orm.Required(int, min=1, max=3)  # 1 = waiting for approval, 2 = public, 3 = expired
        invite_code = orm.Required(str, unique=True)
        server_id = orm.Required(int, unique=True)
        server_name = orm.Required(str, max_len=32)
        description = orm.Required(str, max_len=100)
        invitee_id = orm.Required(int)
        submitted_at = orm.Required(datetime.datetime)
        category_channel_name = orm.Required(str)
        index_message_id = orm.Optional(int)
        last_checked = orm.Required(datetime.datetime)

        # self.db.DiscordServer(state=1,
        #                       invite_code='code',
        #                       server_id=123,
        #                       server_name='Name',
        #                       description='description',
        #                       invitee_id=456,
        #                       submitted_at=datetime.datetime.now(),
        #                       category_channel_name="a",
        #                       index_message_id=789,
        #                       last_checked=datetime.datetime.now())
        # orm.commit()
