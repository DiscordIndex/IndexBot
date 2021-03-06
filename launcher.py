import atexit
import copy
import logging
import os
import signal
import subprocess
import sys

import gevent


class BotSupervisor(object):
    def __init__(self, env={}):
        self.proc = None
        self.env = env
        self.bind_signals()
        self.start()

    def bind_signals(self):
        signal.signal(signal.SIGUSR1, self.handle_sigusr1)

    def handle_sigusr1(self, signum, frame):
        print
        'SIGUSR1 - RESTARTING'
        gevent.spawn(self.restart)

    def start(self):
        env = copy.deepcopy(os.environ)
        env.update(self.env)
        self.proc = subprocess.Popen([sys.executable, '-m', 'disco.cli', '--config', 'config.yaml'], env=env)

    def stop(self):
        self.proc.terminate()

    def restart(self):
        try:
            self.stop()
        except:
            pass

        self.start()

    def run_forever(self):
        while True:
            self.proc.wait()
            gevent.sleep(5)


def exit_handler(logging, supervisor):
    logging.info("shutting down…")
    supervisor.stop()


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    import logging

    logging.info("booting Bot…")
    supervisor = BotSupervisor()

    atexit.register(exit_handler, logging=logging, supervisor=supervisor)

    supervisor.proc.wait()
