# BangBangController

An application that allows you to control various processes using relays and thresholds

In control theory, bang bang controllers are essentially on-off controllers that switch between two states (no proportional control). 

In this case, we want to read JSON serialized SensorMessageItems (see the Aretas API for definition / contract) and control various relay outputs based on defined thresholds. When the thresholds are exceeded (or undershot) for a certain duration we activate the relay. There must also be the concept of "fuzz" or precision so we don't flap from noise. We may also need additional hysteresis. We may also want maximum ON state. 

We map the types to known SensorMetadata in the Aretas API. 

We might define a control strategy like this:

MAC,TYPE,THRESHOLD,THRESHOLD_TYPE,DURATION_REQUIRED
