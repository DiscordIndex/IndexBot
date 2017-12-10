from pony import orm


def define_user_blacklist(db):
    class UserBlacklist(db.Entity):
        user_id = orm.PrimaryKey(int, size=64)
        reason = orm.Required(str, max_len=1000)
        blacklisted_by_user_id = orm.Required(int, size=64)
