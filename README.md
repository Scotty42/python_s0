Requirements for this project:
* count impulse on gpio 
* measure time between two pulses 
* calculate and aggregate total number of pulses into kWh energy 
* use delta time between impulses to calculate average power
* transfer power and energy to MQTT broker

Hints:
* Ensure user account used to run iobroker-client.py is member of groups that own gpio devices. Like kmem, gpio, uucp.
* To run as a systemd service, a sample service file is included. Change and use to fit the target system.

Example systemd log:
`Nov 02 18:49:59 easymeter __main__[11923]: [INFO] last_i: 13, last_t: 0.994, imp: 8994, kwh: 976.5, kw: 3.6`
`Nov 02 18:52:59 easymeter __main__[11923]: [INFO] last_i: 6, last_t: 2.379, imp: 9162, kwh: 976.6, kw: 1.5`

