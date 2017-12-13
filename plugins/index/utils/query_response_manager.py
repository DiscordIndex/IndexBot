import time
from threading import Thread

from disco.api.http import APIException


class QueryResponseManager:
    def __init__(self, callback, cancel_keywords=['cancel'], timeout=120):
        self.timeout = timeout
        self.sessions = []
        self.cancel_keywords = cancel_keywords
        self.callback = callback

    def start_query(self, plugin, user_id, channel_id, message, more_args=None):
        query_message = plugin.client.api.channels_messages_create(channel_id, message)

        self.sessions.append({
            'user_id': user_id,
            'channel_id': channel_id,
            'query_message_id': query_message.id,
            'more_args': more_args
        })

        thread = Thread(target=self.wait_for_withdrawal, args=(plugin, user_id, channel_id))
        thread.start()

    def handle_possible_response(self, plugin, message):
        fitting_session = None

        for session in self.sessions:
            if session['user_id'] == message.author.id and session['channel_id'] == message.channel.id:
                fitting_session = session

        if not fitting_session:
            return

        if message.content.strip().lower() in self.cancel_keywords:
            self.sessions.remove(fitting_session)
            try:
                plugin.client.api.channels_messages_delete(fitting_session['channel_id'],
                                                           fitting_session['query_message_id'])
                message.delete()
            except APIException:
                pass
            return

        self.callback(plugin=plugin, user_id=message.author.id, text=message.content,
                      more_args=fitting_session['more_args'])
        self.sessions.remove(fitting_session)

        try:
            plugin.client.api.channels_messages_delete(fitting_session['channel_id'],
                                                       fitting_session['query_message_id'])
            message.delete()
        except APIException:
            pass

    def wait_for_withdrawal(self, plugin, user_id, channel_id):
        time.sleep(self.timeout)
        self.withdraw_query(plugin, user_id, channel_id)

    def withdraw_query(self, plugin, user_id, channel_id):
        fitting_session = None

        for session in self.sessions:
            if session['user_id'] == user_id and session['channel_id'] == channel_id:
                fitting_session = session

        if not fitting_session:
            return

        self.sessions.remove(fitting_session)
        plugin.client.api.channels_messages_delete(fitting_session['channel_id'],
                                                   fitting_session['query_message_id'])
