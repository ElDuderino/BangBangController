import time


class BangBangController:
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


sensor = MockSensor()
relay_control = BangBangController(sensor, threshold_high=60, threshold_low=40, duration=5)

while True:
    relay_control.check_thresholds()
    time.sleep(1)  # Check every 1 second
