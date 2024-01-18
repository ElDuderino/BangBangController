Relay Controller Control Configuration 

Requirements for a valid control definition

Basics

- JSON formatted config file
- Array of Control Definition objects

Required JSON object key/values:

1) **uuid**: Control definition has a *unique* UUID from all the rest
2) **description**: User friendly description of the control definition
3) **macs**: A single mac or a list of valid mac addresses. 
4) **sensor_types**: one or many sensor types that match the requirement
5) **threshold_value**: the value that triggers the control condition
6) **hysteresis**: a “padding” value that is added or subtracted from the threshold\_value to trigger the back to normal condition. For example, if the threshold\_value is 4.2, the control is an overshoot type, and the hysteresis value is 0.2, the voltage must go below 4.0 volts to enable the back to normal command. 
7) **threshold_type**: 1* represents an overshoot threshold type -1 represents an undershoot threshold type (the value must go below the threshold to trigger)
8) **threshold_duration_millis**: the amount of time (in milliseconds) that the value must exceed the threshold (continuously). If the threshold duration is set to 60000 this means 60 seconds. If the bus reports data every 10 seconds, this means the value must be exceeded for at least 6 consecutive readings
9) **control_channel**: the channel that will be triggered on the relay board (typically 1-8)
10) **control_func**: the function to execute when the threshold is triggered (1 for relay on, 0 for relay off) future options include (flash a light, beep an alert, etc.)
11) **back_to_normal_func**: the function to execute on the relay controller when the threshold (including hysteresis) returns back to normal
12) **fuzz_ms**: this is the amount of fuzziness to incorporate into the duration checking routine. If packets do not arrive in exact intervals or there’s slight lag, set this to a value that will still trigger the alert if packets are a few hundred milliseconds out of order. 
13) **allow_back_to_normal**: True or False – determines whether to allow the controller to execute the back to normal command. For example, if set to False, and the threshold is exceeded and a relay opened. The relay will not close again when the value returns below the threshold. 

Notes

- the same sensor type that triggers the alert (out of the list) must be the same that ‘returns to normal’ to trigger the hysteresis check and back to normal condition, AND:
- the same mac that triggers the control strategy, must be the same that ‘returns to normal’ to trigger the hysteresis check and back to normal condition

