Requirements for this project:
* count impulse on gpio 
* measure time between two pulses 
* calculate and aggregate total number of pulses into kWh energy 
* use delta time between impulses to calculate average power
* transfer power and energy to MQTT broker

Hints:
* Ensure user account used to run iobroker-client.py is member of groups that own gpio devices. Like kmem, gpio, uucp.
* To run as a systemd service, a sample service file is included. Change and use to fit the target system.


