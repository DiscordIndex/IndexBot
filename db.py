import logging

from pony import orm

from models.discordserver import define_discordserver
from models.user_blacklist import define_user_blacklist


class DbHandler(object):
    def __init__(self):
        logging.info("connecting to DB…")
        # orm.set_sql_debug(True)
        self.db = orm.Database(provider='sqlite', filename='database.sqlite', create_db=True)
        define_discordserver(self.db)
        define_user_blacklist(self.db)
        self.db.generate_mapping(create_tables=True)

    def getDb(self):
        return self.db
