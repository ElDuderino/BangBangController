import logging
from multiprocessing import Queue, Event

import numpy as np
import matplotlib.pyplot as plt
import datetime
import time
import scipy.signal as sg
from bang_bang_controller import BangBangController
from sensor_message_item import SensorMessageItem

# An example of using logging.basicConfig rather than logging.fileHandler()
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def sine_wave(x, min_max_range, frequency):
    min_val, max_val = min_max_range
    amplitude = (max_val - min_val) / 2

    # Convert frequency from milliseconds to seconds
    frequency_sec = frequency / 1000.0

    # Generate the sine wave
    y = amplitude * np.sin(2 * np.pi * (x / frequency_sec)) + amplitude + min_val

    return y


def triangle_wave_sg(x, min_max_range, frequency):
    min_val, max_val = min_max_range
    amplitude = (max_val - min_val)
    y = amplitude * sg.sawtooth(frequency * 2 * np.pi * x, width=0.5)
    return y


def triangle_wave(x, min_max_range, frequency):
    min_val, max_val = min_max_range
    amplitude = (max_val - min_val)
    min_val = min_val - amplitude

    # Convert frequency from milliseconds to seconds for compatibility with numpy
    frequency_sec = frequency / 1000.0

    # Generate the triangle wave
    y = amplitude * np.abs(2 * (x / frequency_sec - np.floor(0.5 + x / frequency_sec))) + amplitude + min_val

    return y


def plot_temperature(x_values, y_values, title):
    # Convert current time in milliseconds to a datetime object
    current_time = int(time.time() * 1000)
    current_datetime = datetime.datetime.fromtimestamp(current_time / 1000)

    # Create future datetime objects by adding x values (milliseconds) to current time
    x_datetimes = [current_datetime + datetime.timedelta(milliseconds=int(x)) for x in x_values]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(x_datetimes, y_values, label='Temperature')
    plt.xlabel('Time')
    plt.ylabel('Temperature')
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    plt.show()


def main():
    # simulate 2 hours of data at 30 second intervals

    # Example usage
    time_range = 2 * 60 * 60 * 1000  # 2 hours
    interval = 30 * 1000  # every 30 seconds
    n_values = int(time_range / interval)

    x_values = np.linspace(0, time_range, n_values)  # x values in milliseconds
    min_max_range = (20, 30)  # Simulated temperature range

    # how often does the temperature go through a complete cycle from 20 to 30
    frequency = 120000  # Frequency in milliseconds (2 minutes)

    temperature_values = triangle_wave(x_values, min_max_range, frequency)

    plot_temperature(x_values, temperature_values, 'Simulated Temperature Over Time')

    sensor_message_items: list[SensorMessageItem] = list()

    for i, sensor_value in enumerate(temperature_values):
        timestamp = x_values[i]
        sensor_message_item = SensorMessageItem(303721692, 248, float(sensor_value), int(timestamp))
        sensor_message_items.append(sensor_message_item)

    message_queue = Queue()
    sig_event = Event()
    bang_bang_controller = BangBangController(message_queue, sig_event)
    bang_bang_controller.start()

    # now do the simulation
    for sensor_message_item in sensor_message_items:
        print("Injecting sensor message:{}".format(sensor_message_item))
        message_queue.put(sensor_message_item)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
