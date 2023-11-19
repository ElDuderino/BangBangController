import configparser
import logging
import time
from multiprocessing import Queue, Event
from threading import Thread

from control_defs import ControlDefUtils, ControlDef, ThresholdType, ControlFunc
from sensor_message_item import SensorMessageItem


class BangBangControllerDumb:
    def __init__(self, sensor, threshold_high, threshold_low, duration):
        self.sensor = sensor
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low
        self.duration = duration
        self.last_switch_time = time.time()
        self.relay_state = False

    def read_sensor(self):
        # Replace this with your actual sensor reading code
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


class ControlTrigger:

    def __init__(self, time_exceeded_millis: int, expire_millis: int, sensor_data: float):
        self._time_exceeded_millis = time_exceeded_millis
        self._sensor_data = sensor_data
        self._expire_millis = expire_millis

    def get_time_exceeded_millis(self) -> int:
        return int(self._time_exceeded_millis)

    def get_sensor_data(self) -> float:
        return float(self._sensor_data)

    def get_expire_millis(self) -> int:
        return self._expire_millis


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

        self.control_defs_file = config.get("DEFAULT", "control_defs_file")

        self.control_defs = ControlDefUtils.fetch_control_defs(self.control_defs_file)

        self.control_triggers: dict[str, ControlTrigger] = dict()

    def process_message(self, sensor_message: SensorMessageItem):
        """
        Process incoming sensor messages
        :param sensor_message:
        :return:
        """
        for control_def in self.control_defs:
            if sensor_message.get_mac() in control_def.get_macs():
                exceeded = self.check_thresholds(sensor_message, control_def)
                self.do_post_threshold_logic(sensor_message, control_def, exceeded)

    def do_post_threshold_logic(self, sensor_message: SensorMessageItem, control_def: ControlDef, exceeded: bool):

        key = control_def.get_uuid() + str(sensor_message.get_mac())
        control_trigger = self.control_triggers.get(key, None)

        if exceeded is True and control_trigger is not None:
            pass
        if exceeded is True and control_trigger is None:
            now = int(time.time() * 1000)
            expire = now + int(control_def.get_threshold_duration_millis() * 1.2)

            trigger = ControlTrigger(now, expire, sensor_message.get_data())
            self.control_triggers[key] = trigger

        if exceeded is False and control_trigger is not None:
            # we have an existing control trigger, and we've returned to a non-aberrant state
            # we don't want flapping so we check to see if the value has exceeded the hysteresis point
            # check the various hystereses

            pass
    
    def check_hysteresis(self, sensor_message: SensorMessageItem, control_def: ControlDef):

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

    def run(self):
        while True:

            while not self.message_queue.empty():
                # process messages in the queue
                pass

            if self.sig_event.is_set():
                print("Exiting {}".format(self.__class__.__name__))
                break

            if self.thread_sleep is True:
                time.sleep(self.cache_fetch_interval_ms / 1000.0)


"""
sensor = MockSensor()
relay_control = BangBangController(sensor, threshold_high=60, threshold_low=40, duration=5)

while True:
    relay_control.check_thresholds()
    time.sleep(1)  # Check every 1 second
"""
