from enum import IntEnum


class ThresholdType(IntEnum):
    OVERSHOOT = 1
    UNDERSHOOT = -1


class ControlFunc(IntEnum):
    ON = 1
    OFF = 0


class ControlDef:
    """
    "uuid": "941a5640-82ac-11ee-b962-0242ac120002",
    "macs": [],
    "sensor_type": 248,
    "threshold_value": 23.0,
    "hysteresis": 0.5,
    "threshold_type": -1,
    "threshold_duration_millis": 30000,
    "control_func": 0,
    "control_channel": 1
    """

    def __init__(self,
                 uuid: str = None,
                 macs: set = None,
                 sensor_type: int = None,
                 threshold_value: float = None,
                 hysteresis: float = None,
                 threshold_type: ThresholdType = None,
                 threshold_duration_millis: int = None,
                 control_func: ControlFunc = None,
                 control_channel: int = None):
        self._uuid: str = uuid
        self._macs: set = macs
        self._sensor_type: int = sensor_type
        self._threshold_value: float = threshold_value
        self._hysteresis: float = hysteresis
        self._threshold_type: ThresholdType = threshold_type
        self._threshold_duration_millis = threshold_duration_millis
        self._control_func: ControlFunc = control_func
        self._control_channel = control_channel

    def get_uuid(self) -> str:
        return self._uuid

    def set_uuid(self, uuid: str):
        self._uuid = uuid

    def get_macs(self) -> set:
        return self._macs

    def set_macs(self, macs: set):
        self._macs = macs

    def get_sensor_type(self) -> int:
        return self._sensor_type

    def set_sensor_type(self, sensor_type: int):
        self._sensor_type = sensor_type

    def get_threshold_value(self) -> float:
        return self._threshold_value

    def set_threshold_value(self, threshold_value: float):
        self._threshold_value = threshold_value

    def get_hysteresis(self) -> float:
        return self._hysteresis

    def set_hysteresis(self, hysteresis: float):
        self._hysteresis = hysteresis

    def get_threshold_type(self) -> ThresholdType:
        return self._threshold_type

    def set_threshold_type(self, threshold_type: ThresholdType):
        self._threshold_type = threshold_type

    def get_threshold_duration_millis(self) -> int:
        return self._threshold_duration_millis

    def set_threshold_duration_millis(self, threshold_duration_millis: int):
        self._threshold_duration_millis = threshold_duration_millis
