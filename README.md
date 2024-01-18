# BangBangController

An application that allows you to control various processes using relays and thresholds

In control theory, bang bang controllers are essentially on-off controllers that switch between two states (no proportional control). 

In this case, we want to read JSON serialized SensorMessageItems (see the Aretas API for definition / contract) and control various relay outputs based on defined thresholds. 
When the thresholds are exceeded (or undershot) for a certain duration we activate the relay. 
There must also be the concept of "fuzz" or precision so we don't flap from noise. 
We may also need additional hysteresis. We may also want maximum ON state. 

We map the types to known SensorMetadata in the Aretas API. 

## Logging

Log files go into the project folder as "RelayController.log" by default. Log files are rotated. 
To change the default logging behaviour, edit ``backend_daemon.py`` and change the following lines at
the top of the file:
``logging.basicConfig(level=logging.DEBUG,
                    handlers=[
                        RotatingFileHandler("RelayController.log", maxBytes=50000000, backupCount=5)
                    ],
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")``
                    
Watching logs:

Under Linux: ``tail -f RelayController.log``
Under Windows (use PowerShel): ``Get-Content RelayController.log -Wait -Tail 30``

 
## Git stuff
If you're working from the Git repo, you will need to add / clone the submodules

In addition, if you want to update to the latest version of submodules, navigate into the project
sub folder and run:
``git submodule update --remote --merge``
