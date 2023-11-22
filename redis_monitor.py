import configparser
import logging
import time
from multiprocessing import Queue, Event
from threading import Thread
import json
import jsonpickle
import redis

from WaveshareRelayControl.waveshare_defs import WaveshareDef
from control_defs import ControlDef, ThresholdType, ControlFunc, ControlDefUtils
from sensor_message_item import SensorMessageItem


class RedisMonitor(Thread):

    def __init__(self, message_queue: Queue, sig_event: Event):

        super(RedisMonitor, self).__init__()

        self.logger = logging.getLogger(__name__)
        self.logger.info("Init Redis Monitor")

        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')

        redis_host = config.get("REDIS", "redis_host", fallback="localhost")
        redis_port = config.getint("REDIS", "redis_port", fallback=6379)
        redis_password = config.get("REDIS", "redis_authpw", fallback="FooBaz")
        self.r = redis.StrictRedis(redis_host, redis_port, password=redis_password, decode_responses=True)
        self.cache_fetch_interval_ms = config.getint("REDIS", "cache_fetch_interval", fallback=3000)
        self.thread_sleep = True

        self.control_defs_file = config.get("DEFAULT", "control_defs_file")

        self.message_queue = message_queue
        self.sig_event = sig_event

        self.logger.info("Loading control defs")
        self.control_defs = ControlDefUtils.fetch_control_defs(self.control_defs_file)
        self.logger.info("Finished loading control defs")

        self.observables = ControlDefUtils.get_observables(self.control_defs)

        self.last_sensor_messages: dict[int, dict] = dict()

    def get_message_safe(self, sensor_message: SensorMessageItem) -> SensorMessageItem | None:
        sensor_type_dict = self.last_sensor_messages.get(sensor_message.get_mac(), None)
        if sensor_type_dict is None:
            return None
        else:
            sensor_message = sensor_type_dict.get(sensor_message.get_type(), None)
            return sensor_message  # returning sensor message or None

    def deduplicate_sensor_messages(self, sensor_messages: list[SensorMessageItem]):
        """
        This function mutates the global self.last_sensor_messages dict
        Call it directly after fetching messages from the cache
        :param sensor_messages:
        :return:
        """
        for sensor_message in sensor_messages:
            # check if the message is in the last_messages dict
            # if not, then add it
            # otherwise check if the incoming message is newer than the one in the dict
            # if it's not, then do nothing
            # if it is, then replace the message
            sensor_type_dict = self.last_sensor_messages.get(sensor_message.get_mac(), None)
            if sensor_type_dict is None:
                sensor_type_dict = dict()
                self.last_sensor_messages[sensor_message.get_mac()] = sensor_type_dict
                sensor_type_dict[sensor_message.get_type()] = sensor_message
                continue
            else:
                # perhaps the type does not exist
                sensor_type_message: SensorMessageItem = sensor_type_dict.get(sensor_message.get_type(), None)
                if sensor_type_message is None:
                    sensor_type_dict[sensor_message.get_type()] = sensor_message
                    continue
                else:
                    if sensor_type_message.get_timestamp() < sensor_message.get_timestamp():
                        sensor_type_dict[sensor_message.get_type()] = sensor_message
                        continue
                    else:
                        pass
                        continue

    def fetch_redis_messages(self) -> list[SensorMessageItem]:
        """
        Fetch the messages from the redis cache and run the deduplication logic
        :return:
        """
        sensor_messages = list()

        # we only fetch MACS that are in control_defs
        for mac in self.observables.keys():
            try:
                redis_results = self.r.hgetall(str(mac))
                for redis_result_key in redis_results.keys():
                    redis_result = redis_results[redis_result_key]
                    sensor_message_item: SensorMessageItem = jsonpickle.decode(redis_result)

                    # check if the type is in the allowed observables
                    if int(sensor_message_item.get_type()) in (self.observables[mac]):
                        self.logger.debug("Queuing cache message:{}".format(sensor_message_item))
                        sensor_messages.append(sensor_message_item)

            # try and get more specific with this
            except Exception as e:
                self.logger.error("Error fetching sensor messages:{}", e)

        # deduplicate the messages in the queue
        self.deduplicate_sensor_messages(sensor_messages)

    def inject_messages(self):
        n_injected_messages = 0
        # here we decide whether to send the messages
        # in the global storage dict based on whether
        # they are flagged as sent
        for mac in self.last_sensor_messages.keys():
            sensor_type_dict = self.last_sensor_messages[mac]
            for sensor_type in sensor_type_dict.keys():
                sensor_message: SensorMessageItem = sensor_type_dict[sensor_type]
                if sensor_message.get_is_sent() is False:
                    self.message_queue.put(sensor_message)
                    sensor_message.set_is_sent(True)
                    n_injected_messages += 1

        self.logger.debug("Injected {} messages".format(n_injected_messages))

    def run(self):
        while True:

            self.logger.debug("Fetching REDIS cache messages")
            self.fetch_redis_messages()
            self.inject_messages()

            if self.sig_event.is_set():
                print("Exiting {}".format(self.__class__.__name__))
                break

            if self.thread_sleep is True:
                time.sleep(self.cache_fetch_interval_ms / 1000.0)
