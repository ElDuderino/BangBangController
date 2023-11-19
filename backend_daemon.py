"""
1. Read in the alert definitions
2. Spawn a class that gives us relay control
3. Loop and read the sensor messages from the cache (but only for the MACs and types specified in the control defs)
4. When a message "arrives" check it against the control defs and execute the control logic

Since we're reading redis fairly fast, and we don't know the frequency of messages coming in, we might
want to have a deduplication thread where a thread just watches the cache and injects only new messages into a queue

"""
from threading import Event
from queue import Queue
import configparser
import logging
from logging.handlers import RotatingFileHandler

from redis_monitor import RedisMonitor

# An example of using logging.basicConfig rather than logging.fileHandler()
logging.basicConfig(level=logging.DEBUG,
                    handlers=[
                        RotatingFileHandler("RelayController.log", maxBytes=50000000, backupCount=5)
                    ],
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import signal

    # read in the global app config
    config = configparser.ConfigParser()
    config.read('config.cfg')

    # this is a shared event handler among all the threads
    thread_sig_event = Event()

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C!')
        thread_sig_event.set()

    # define the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    # this is the shared message queue for the redis message harvester and the controller
    mq_payload_queue: Queue = Queue()

    logger.info("Redis Cache Monitor thread starting:")
    redis_monitor_thread = RedisMonitor(mq_payload_queue, thread_sig_event)
    redis_monitor_thread.start()
    logger.info("Redis Cache Monitor thread started.")

    logger.info("Message harvester thread starting:")
    message_harvester_thread = MessageHarvester(mq_payload_queue,
                                                thread_sig_event)
    message_harvester_thread.start()
    logger.info("Message harvester thread started.")

    # Test setting the termination event
    # print("Setting thread_sig_event")
    # thread_sig_event.set()

    serial_port_thread.join()
    message_harvester_thread.join()