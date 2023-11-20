class SensorMessageItem:
    """
    A contract for the sensor message item type

    Note that all the superfluous type conversions are due
    to jsonpickle not deserializing types correctly
    """

    def __init__(self, mac: int = -1,
                 sensor_type: int = -1,
                 payload_data: float = -1.0,
                 timestamp: int = -1,
                 sent: bool = False):
        self._mac: int = mac
        self._type: int = sensor_type
        self._data: float = payload_data
        self._timestamp: int = timestamp
        self._sent: bool = sent
        pass

    def __repr__(self):
        return ("{{ sensor_type:{}, mac:{}, timestamp:{}, data:{} sent:{} }}".format(
            self._type,
            self._mac,
            self._timestamp,
            self._data,
            self._sent
        ))

    def get_type(self) -> int:
        return int(self._type)

    def set_type(self, sensor_type: int):
        self._type = int(sensor_type)

    def get_data(self) -> float:
        return float(self._data)

    def set_data(self, payload_data: float):
        self._data = float(payload_data)

    def get_timestamp(self) -> int:
        return int(self._timestamp)

    def set_timestamp(self, timestamp: int):
        self._timestamp = int(timestamp)

    def get_mac(self) -> int:
        return int(self._mac)

    def set_mac(self, mac: int):
        mac = int(mac)
        self._mac = mac

    def get_is_sent(self) -> bool:
        return bool(self._sent)

    def set_is_sent(self, is_sent: bool):
        self._sent = bool(is_sent)
