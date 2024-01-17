from enum import IntEnum
import json
from WaveshareRelayControl.waveshare_defs import WaveshareDef


class ThresholdType(IntEnum):
    OVERSHOOT = 1
    UNDERSHOOT = -1

    @staticmethod
    def from_int(thresh_type: int):
        if thresh_type == 1:
            return ThresholdType.OVERSHOOT
        elif thresh_type == -1:
            return ThresholdType.UNDERSHOOT
        else:
            return None


class ControlFunc(IntEnum):
    ON = 1
    OFF = 0

    @staticmethod
    def from_int(control_func):
        if control_func == 1:
            return ControlFunc.ON
        elif control_func == 0:
            return ControlFunc.OFF
        else:
            return None


class ControlDef:
    """
    Contract for the Control Definition

    "uuid": "941a5640-82ac-11ee-b962-0242ac120002",
    "macs": [],
    "sensor_type": 248,
    "threshold_value": 23.0,
    "hysteresis": 0.5,
    "threshold_type": -1,
    "threshold_duration_millis": 30000,
    "control_func": 1,
    "control_channel": 1
    "back_to_normal_func": 0
    "fuzz_ms": 500
    """

    def __init__(self,
                 uuid: str = None,
                 macs: set = None,
                 sensor_types: list[int] = None,
                 threshold_value: float = None,
                 hysteresis: float = None,
                 threshold_type: ThresholdType = None,
                 threshold_duration_millis: int = None,
                 control_func: ControlFunc = None,
                 control_channel: WaveshareDef = None,
                 back_to_normal_func: ControlFunc = None,
                 allow_back_to_normal: bool = None,
                 fuzz_ms: float = 0.0):
        self._uuid: str = uuid

        if macs is None:
            self._macs = set()
        else:
            self._macs = macs

        self._sensor_types: int = sensor_types
        self._threshold_value: float = threshold_value
        self._hysteresis: float = hysteresis
        self._threshold_type: ThresholdType = threshold_type
        self._threshold_duration_millis = threshold_duration_millis
        self._control_func: ControlFunc = control_func
        self._control_channel: WaveshareDef = control_channel
        self._back_to_normal_func: ControlFunc = back_to_normal_func
        self._allow_back_to_normal = allow_back_to_normal
        self._fuzz_ms = fuzz_ms

    def get_uuid(self) -> str:
        return self._uuid

    def set_uuid(self, uuid: str):
        self._uuid = uuid

    def get_macs(self) -> set:
        return self._macs

    def set_macs(self, macs: set):
        self._macs = macs

    def get_sensor_types(self) -> list[int]:
        return self._sensor_types

    def set_sensor_type(self, sensor_types: list[int]):
        self._sensor_types = sensor_types

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

    def get_control_func(self) -> ControlFunc:
        return self._control_func

    def set_control_func(self, control_func: ControlFunc):
        self._control_func = control_func

    def get_control_channel(self) -> WaveshareDef:
        return self._control_channel

    def set_control_channel(self, control_channel: WaveshareDef):
        self._control_channel = control_channel

    def set_back_to_normal_func(self, back_to_normal_func: ControlFunc):
        self._back_to_normal_func = back_to_normal_func

    def get_back_to_normal_func(self) -> ControlFunc:
        return self._back_to_normal_func

    def set_allow_back_to_normal(self, allow_back_to_normal:bool):
        self._allow_back_to_normal = allow_back_to_normal

    def get_allow_back_to_normal(self)->bool:
        return self._allow_back_to_normal

    def set_fuzz_ms(self, fuzz_ms: float):
        self._fuzz_ms = fuzz_ms

    def get_fuzz_ms(self)-> float:
        return self._fuzz_ms


class ControlDefUtils:

    @staticmethod
    def fetch_control_defs(control_defs_file: str) -> list[ControlDef]:
        """
        Fetch the control definitions (for now from JSON, in the future from cloud)
        :return:
        """

        ret = list()

        # for now we depend on a static control defs file
        with open(control_defs_file) as control_defs:
            file_contents = control_defs.read()

        control_defs = json.loads(file_contents)
        for control_def in control_defs:
            ret.append(ControlDef(control_def["uuid"],
                                  set(control_def["macs"]),
                                  list(control_def["sensor_types"]),
                                  float(control_def["threshold_value"]),
                                  float(control_def["hysteresis"]),
                                  ThresholdType.from_int(int(control_def["threshold_type"])),
                                  int(control_def["threshold_duration_millis"]),
                                  ControlFunc.from_int(int(control_def["control_func"])),
                                  WaveshareDef.from_channel_def(
                                      int(control_def["control_channel"])),
                                  ControlFunc.from_int(int(control_def["back_to_normal_func"])),
                                  float(control_def["fuzz_ms"])))

        return ret

    @staticmethod
    def get_observables(control_defs: list[ControlDef]) -> dict[int, set]:
        """
        Return a list of cache observables
        :return:
        """
        observables_dict = dict()

        for control_def in control_defs:
            macs = control_def.get_macs()
            sensor_types = control_def.get_sensor_types()
            for mac in macs:
                mac_observable_set = observables_dict.get(mac)
                if mac_observable_set is None:
                    mac_observable_set = set()
                    observables_dict[mac] = mac_observable_set
                for sensor_type in sensor_types:
                    mac_observable_set.add(sensor_type)

        return observables_dict
