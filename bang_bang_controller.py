import configparser
import logging
import time
from multiprocessing import Queue, Event
from threading import Thread

import requests
import urllib3

from AretasPythonAPI.api_config import APIConfig
from AretasPythonAPI.auth import APIAuth
from AretasPythonAPI.sensor_data_ingest import SensorDataIngest
from WaveshareRelayControl.relaycontrolmain import WaveshareRelayController
from control_defs import ControlDefUtils, ControlDef, ThresholdType, ControlFunc
from sensor_message_item import SensorMessageItem


class ControlTrigger:
    """
    The control trigger will keep information about the Control Def execution in memory (or cache eventually)
    """

    def __init__(self, time_exceeded_millis: int, expire_millis: int, sensor_data: float):
        self._time_exceeded_millis = time_exceeded_millis
        self._sensor_data = sensor_data
        self._expire_millis = expire_millis

        # when did we last see this sensor?
        self._last_sensor_read_ms = None
        self._last_sensor_data = None

        # when did we execute the control function
        self._control_func_execute_time_ms = None

    def get_time_exceeded_millis(self) -> int:
        return int(self._time_exceeded_millis)

    def get_sensor_data(self) -> float:
        return float(self._sensor_data)

    def get_expire_millis(self) -> int:
        return self._expire_millis

    def set_last_sensor_read_ms(self, last_sensor_read_ms: int):
        self._last_sensor_read_ms = last_sensor_read_ms

    def get_last_sensor_read_ms(self) -> int:
        return self._last_sensor_read_ms

    def set_last_sensor_data(self, last_sensor_data: float):
        self._last_sensor_data = last_sensor_data

    def get_last_sensor_data(self) -> float:
        return self._last_sensor_data

    def set_control_func_execution_time_ms(self, control_func_execution_time_ms: int):
        self._control_func_execute_time_ms = control_func_execution_time_ms

    def get_control_func_execution_time_ms(self) -> int | None:
        return self._control_func_execute_time_ms


class BangBangController(Thread):

    def __init__(self, message_queue: Queue, sig_event: Event):

        super(BangBangController, self).__init__()

        self.logger = logging.getLogger(__name__)
        self.logger.info("Init Controller")

        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')

        self.message_queue = message_queue
        self.sig_event = sig_event

        self.api_update_interval = config.getint('DEFAULT', 'api_update_interval')
        self.api_mac = config.getint('DEFAULT', 'api_mac')

        self.api_config = APIConfig()
        self.api_auth = APIAuth(self.api_config)
        self.api_writer = SensorDataIngest(self.api_auth)

        self.last_api_update_time = 0

        self.thread_sleep = config.getboolean('DEFAULT', 'thread_sleep')
        self.thread_sleep_time = config.getfloat('DEFAULT', 'thread_sleep_time')

        self.control_defs_file = config.get("DEFAULT", "control_defs_file")

        self.control_defs = ControlDefUtils.fetch_control_defs(self.control_defs_file)

        self.control_triggers: dict[str, ControlTrigger] = dict()

        serial_port = config.get("RELAY_CONTROLLER", "serial_port", fallback="/dev/ttyUSB0")
        set_default_state_at_boot = config.getboolean("RELAY_CONTROLLER", "set_default_state_at_boot", fallback=False)

        default_states_str = config.get("RELAY_CONTROLLER", "default_relay_states", fallback=None)
        default_states_dict = WaveshareRelayController.parse_default_states(default_states_str)

        self.relay_controller = WaveshareRelayController(serial_port, default_states=default_states_dict)
        if set_default_state_at_boot is True:
            self.relay_controller.set_default_states()

        # track how many messages we've processed
        self.n_messages_processed = 0

        self.cache_fetch_interval_ms = config.getint("REDIS", "cache_fetch_interval_ms", fallback=30000)

    def process_message(self, sensor_message: SensorMessageItem):
        """
        Process incoming sensor messages
        :param sensor_message:
        :return:
        """
        self.n_messages_processed += 1

        if (self.n_messages_processed % 400) == 0:
            self.logger.info("Processed {} messages".format(self.n_messages_processed))

        for control_def in self.control_defs:
            # check if the mac and the sensor type match the control strategy
            if (sensor_message.get_mac() in control_def.get_macs()) and (
                    sensor_message.get_type() in control_def.get_sensor_types()):
                exceeded = self.exceeded_threshold(sensor_message, control_def)
                self.do_post_threshold_logic(sensor_message, control_def, exceeded)

    def do_post_threshold_logic(self, sensor_message: SensorMessageItem, control_def: ControlDef, exceeded: bool):

        key = BangBangController.get_control_trigger_key(sensor_message, control_def)
        control_trigger = self.control_triggers.get(key, None)

        if (exceeded is True) and (control_trigger is not None):
            # we have a control trigger, meaning the threshold has been previously exceeded
            # AND that this MAC and type has triggered it before
            # have duration_exceeded_millis milliseconds expired since the last trigger?
            # be mindful that there is some drift in message arrival time so if you set it exactly
            # to the message arrival duration, it might not get triggered until the *next* interval unless
            # there is some fuzz_ms added in
            exceeded_duration_ms = BangBangController.exceeded_duration_ms(sensor_message, control_def, control_trigger)

            # check if the control has already been activated
            # note that we MAY want to keep executing the control
            is_on = False
            if control_trigger.get_control_func_execution_time_ms() is not None:
                # it means we already turned on the control
                is_on = True

            if (exceeded_duration_ms is True) and (is_on is False):
                self.logger.debug("ALERT LOGIC: Value has exceeded threshold, duration millis is exceeded, turning "
                                  "control on")
                self.execute_control_command(sensor_message, control_def)
            else:
                self.logger.debug("ALERT LOGIC: Value has exceeded threshold, exceeded_duration_ms:{} control is:{}"
                                  .format(exceeded_duration_ms, is_on))
            return

        if (exceeded is True) and (control_trigger is None):
            # we've exceeded the threshold, and now we need to create a control_trigger to log the action
            # so when the next sensor message comes in from this device, we can check it against the
            # duration requirements
            now = int(time.time() * 1000)
            expire = now + int(control_def.get_threshold_duration_millis() * 1.2)

            # we use the sensor message timestamps for duration exceeded
            trigger = ControlTrigger(sensor_message.get_timestamp(), expire, sensor_message.get_data())
            self.control_triggers[key] = trigger
            self.logger.debug("ALERT LOGIC: value has exceeded the threshold, creating control trigger")
            return

        if (exceeded is False) and (control_trigger is not None):
            # we have an existing control trigger, and we've returned to a non-aberrant state
            # we don't want flapping so we check to see if the value has exceeded the hysteresis point
            # check the various hystereses
            hysteresis_check = self.check_hysteresis(sensor_message, control_def)
            if hysteresis_check is True:

                if control_def.get_allow_back_to_normal():
                    # execute the back to normal command
                    self.logger.debug(
                        "ALERT LOGIC: Threshold is not exceeded, hysteresis check passed, returning to normal")
                    self.execute_back_to_normal_command(sensor_message, control_def)

                else:
                    self.logger.debug("ALERT LOGIC: Threshold not exceeded, hysteresis check passed, \
                    but not allowed to return to normal")

            else:
                self.logger.debug("ALERT LOGIC: Threshold is not exceeded, hysteresis check did not pass")

    @staticmethod
    def get_control_trigger_key(sensor_message: SensorMessageItem, control_def: ControlDef) -> str:
        """
        This key generation is super important, it essentially provides "validation" that the mac and the type match
        when we're inspecting the packet for the control logic.

        :param sensor_message:
        :param control_def:
        :return:
        """
        return "{0}-{1}-{2}".format(sensor_message.get_mac(), sensor_message.get_type(), control_def.get_uuid())

    @staticmethod
    def exceeded_duration_ms(sensor_message: SensorMessageItem,
                             control_def: ControlDef,
                             control_trigger: ControlTrigger) -> bool:
        """
        Check to see if the duration exceeded time has been exceeded but take into account
        any fuzz_ms value that is defined in the control strategy definition
        :param sensor_message:
        :param control_def:
        :param control_trigger:
        :return:
        """
        elapsed = sensor_message.get_timestamp() - control_trigger.get_time_exceeded_millis()
        req_duration = control_def.get_threshold_duration_millis()
        fuzz_ms = control_def.get_fuzz_ms()

        # we only need to be +/- fuzz_ms in elapsed time since exceeding the threshold
        t = elapsed - req_duration

        # the exact amount of time or more time has elapsed
        if t >= 0:
            return True

        # not enough time has elapsed but if it's within fuzz_ms return True
        if t < 0:
            if abs(t) < fuzz_ms:
                return True

        return False

    def execute_control_command(self, sensor_message: SensorMessageItem, control_def: ControlDef):
        """
        Make sure to call this function AFTER creating and adding the control trigger
        :param sensor_message:
        :param control_def:
        :return:
        """
        key = BangBangController.get_control_trigger_key(sensor_message, control_def)
        control_trigger = self.control_triggers.get(key, None)

        if control_def.get_control_func() == ControlFunc.ON:
            self.relay_controller.set_channel_on(control_def.get_control_channel())
        elif control_def.get_control_func() == ControlFunc.OFF:
            self.relay_controller.set_channel_off(control_def.get_control_channel())
        else:
            self.logger.error("Invalid control function {0} for control_def:{1}"
                              .format(control_def.get_control_func(), control_def.get_uuid()))

        # mutate the control trigger
        control_trigger.set_control_func_execution_time_ms(int(time.time() * 1000))

    def execute_back_to_normal_command(self, sensor_message: SensorMessageItem, control_def: ControlDef):
        """
        Make sure to call this function AFTER creating and adding the control trigger
        :param sensor_message:
        :param control_def:
        :return:
        """
        key = BangBangController.get_control_trigger_key(sensor_message, control_def)
        control_trigger = self.control_triggers.get(key, None)

        if control_def.get_back_to_normal_func() == ControlFunc.ON:
            self.relay_controller.set_channel_on(control_def.get_control_channel())
        elif control_def.get_back_to_normal_func() == ControlFunc.OFF:
            self.relay_controller.set_channel_off(control_def.get_control_channel())
        else:
            self.logger.error("Invalid control function {0} for control_def:{1}"
                              .format(control_def.get_control_func(), control_def.get_uuid()))

        _ = self.control_triggers.pop(key)

    def check_hysteresis(self, sensor_message: SensorMessageItem, control_def: ControlDef):
        """
        In a return to normal scenario, we use hysteresis to prevent flapping
        :param sensor_message:
        :param control_def:
        :return:
        """
        if control_def.get_threshold_type() is ThresholdType.OVERSHOOT:
            # check if we've gone back below the threshold
            if sensor_message.get_data() < (control_def.get_threshold_value() - control_def.get_hysteresis()):
                return True
        elif control_def.get_threshold_type() is ThresholdType.UNDERSHOOT:
            # check if we've gone back above the threshold
            if sensor_message.get_data() > (control_def.get_threshold_value() + control_def.get_hysteresis()):
                return True
        else:
            self.logger.error("Invalid ThresholdType:{}".format(control_def.get_threshold_type()))
            return False

    def send_batch_to_api(self, batch: list[dict]) -> bool:
        """
        Send a batch of messages to the API
        If sending is successful, set_is_sent to True
        """
        try:
            # we're using the token self-management function
            err = self.api_writer.send_data(batch, True)
            if err is False:
                self.logger.error("Error sending messages, aborting rest")
                return False
            else:
                return True

        except urllib3.exceptions.ReadTimeoutError as rte:
            '''
            There are a lot of things we need to handle in stateless HTTP land without
            aborting the thread
            '''
            self.logger.error("Read timeout error from urllib3:{}".format(rte))
            # we break because there's no point in trying to send the rest of the messages,
            # we can wait until next interval
            return False

        except requests.exceptions.ReadTimeout as rt:
            self.logger.error("Read timeout error from requests:{}".format(rt))
            return False

        except requests.exceptions.ConnectTimeout as cte:
            self.logger.error("Connection timeout error sending messages to API:{}".format(cte))
            return False

        # we need to be fairly aggressive with exception handling as we are in a thread
        # doing network stuff and network things are buggy as heck
        except Exception as e:
            self.logger.error("Unknown exception trying to send messages to API:{}".format(e))
            return False

    def update_api(self):

        try:
            batch = list()

            now = int(time.time() * 1000)
            channel_states = self.relay_controller.get_channel_states()

            base_type = 0x12D  # 301 sensortype from API

            # we only care about the relay GPIO channels (CH1-8)
            channel_list = ["CH{}".format(i) for i in range(1, 9)]

            for channel, state in channel_states.items():

                # only send state information about the relay channels
                if channel.name not in channel_list:
                    continue

                if state is None:
                    # the state has not been modified by any control action yet
                    state = -1

                datum: dict = {
                    'mac': self.api_mac,
                    'type': base_type + (channel.get_channel_number() - 1),
                    'timestamp': now,
                    'data': state
                }

                batch.append(datum)
            self.logger.info("Sending batch len {} to API:".format(len(batch)))
            self.send_batch_to_api(batch)

        except Exception as e:
            self.logger.error("Unknown exception trying to send messages to API:{}".format(e))
            return False

    def exceeded_threshold(self, sensor_message: SensorMessageItem, control_def: ControlDef) -> bool:
        """
        Check if the sensor data overshot or undershot the threshold
        :param sensor_message:
        :param control_def:
        :return:
        """
        if control_def.get_threshold_type() is ThresholdType.OVERSHOOT:
            # check if we've overshot the threshold
            if sensor_message.get_data() > control_def.get_threshold_value():
                return True
        elif control_def.get_threshold_type() is ThresholdType.UNDERSHOOT:
            # check if we've undershot the threshold
            if sensor_message.get_data() < control_def.get_threshold_value():
                return True
        else:
            self.logger.error("Invalid ThresholdType:{}".format(control_def.get_threshold_type()))
            return False

        return False

    def run(self):
        while True:

            while not self.message_queue.empty():
                # process messages in the queue
                sensor_message_item = self.message_queue.get()
                self.process_message(sensor_message_item)

            # expire old control triggers
            pass
            # refresh control_defs
            pass

            now = int(time.time() * 1000)
            if (now - self.last_api_update_time) >= self.api_update_interval:
                self.logger.info("Updating API statuses")
                self.update_api()
                self.last_api_update_time = now

            if self.sig_event.is_set():
                print("Exiting {}".format(self.__class__.__name__))
                break

            if self.thread_sleep is True:
                time.sleep(self.cache_fetch_interval_ms / 1000.0)


class BangBangControllerDumb:
    def __init__(self, sensor, threshold_high, threshold_low, duration):
        self.sensor = sensor
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low
        self.duration = duration
        self.last_switch_time = time.time()
        self.relay_state = False

    def read_sensor(self):
        return self.sensor.get_value()

    def check_thresholds(self):
        sensor_value = self.read_sensor()
        current_time = time.time()

        if sensor_value > self.threshold_high:
            if current_time - self.last_switch_time >= self.duration and not self.relay_state:
                self.toggle_relay(True)

        elif sensor_value < self.threshold_low:
            if current_time - self.last_switch_time >= self.duration and self.relay_state:
                self.toggle_relay(False)

    def toggle_relay(self, state):
        # Replace this with your actual relay control code
        # e.g., GPIO.output(relay_pin, state)
        self.relay_state = state
        self.last_switch_time = time.time()
        print(f"Relay {'ON' if state else 'OFF'}")


# Example usage
# Assuming a hypothetical sensor class with get_value method
class MockSensor:
    def get_value(self):
        # Simulate sensor value
        return 50


"""
sensor = MockSensor()
relay_control = BangBangControllerDumb(sensor, threshold_high=60, threshold_low=40, duration=5)

while True:
    relay_control.check_thresholds()
    time.sleep(1)  # Check every 1 second
"""
