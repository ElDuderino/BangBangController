"""
1. Read in the alert definitions
2. Spawn a class that gives us relay control
3. Loop and read the sensor messages from the cache (but only for the MACs and types specified in the control defs)
4. When a message "arrives" check it against the control defs and execute the control logic

Since we're reading redis fairly fast, and we don't know the frequency of messages coming in, we might
want to have a deduplication thread where a thread just watches the cache and injects only new messages into a queue

"""