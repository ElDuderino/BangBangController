import logging
from multiprocessing import Event, Queue

from redis_monitor import RedisMonitor

# An example of using logging.basicConfig rather than logging.fileHandler()
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def main():
    sig_event = Event()
    msg_queue = Queue()
    redis_monitor = RedisMonitor(msg_queue, sig_event)
    redis_monitor.start()

    while True:
        pass
    pass


if __name__ == "__main__":
    main()
