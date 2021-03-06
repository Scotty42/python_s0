import paho.mqtt.client as mqtt
import os.path
import time
import systemd.daemon as sd
import logging
from systemd.journal import JournaldLogHandler
import wiringpi

# e.g. IObroker mqtt adapter:
MQTT_PREFIX = "easymeter/ladestation_s0/"

# current counter
INITIAL_VALUE = 978.13

IMPULSE_PER_KWH = 1000
SECONDS_PER_HOUR = 3600
BASE_POWER = 1
STEPS = 1000
POWER_PER_IMP = SECONDS_PER_HOUR / STEPS  # kWs

global_last_time = 0
global_timestamp = 0
global_deltat = 0

global_kw = 0
global_kwh = 0
global_impulse = 0

global_deltai = 0
global_last_imp = 0

# current counter will be persisted in
# touch before first start
DATA_FILE = "/var/lib/ladestation_s0/value"

# get an instance of the logger object this module will use
logger = logging.getLogger(__name__)

# instantiate the JournaldLogHandler to hook into systemd
journald_handler = JournaldLogHandler()

# set a formatter to include the level name
journald_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))

# add the journald handler to the current logger
logger.addHandler(journald_handler)

# optionally set the logging level
logger.setLevel(logging.DEBUG)


def readvalue():
    f = open(DATA_FILE, "r")
    value = float(f.readline())
    f.close()
    return value


def writevalue(value):
    f = open(DATA_FILE, "w")
    f.write(str(value))
    f.close()


def publish(value):
    client.publish(MQTT_PREFIX + "kWh_value", INITIAL_VALUE, qos=0, retain=True)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code {}".format(rc))
    logger.info('Connected with result code {%s}', rc)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

# The callback for when the client receives a CONNACK response from the server.
def on_disconnect(client, userdata, rc):
    print("Disconnected with result code {}".format(rc))
    logger.info('Disconnected with result code {%s}', rc)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    logger.info('%s %s', msg.topic, str(msg.payload))


# The callback for when a PUBLISH message is received from the server.
def on_publish(client, userdata, mid):
    print("Data published. mid: {}".format(mid))
    logger.info('Data published. mid: {%s}', mid)


# callback for gpio
def gpio_callback():
    global global_last_time
    global global_timestamp
    global global_deltat
    global global_impulse
    global global_kw

    # get time stamp
    global_timestamp = time.time()
    if global_last_time > 0:
        global_deltat = global_timestamp - global_last_time
    else:
        global_deltat = 0
    global_last_time = global_timestamp

    # increment if delta t is greater than 30-40ms = min pulse duration for S0
    # otherwise gpio isr triggered more than once for the same S0 pulse
    if global_deltat > 0.04: 
        global_impulse += 1


if __name__ == '__main__':
    print('Starting up ...')
    logger.info('Starting up...')
    time.sleep(3)

    if not os.path.exists(DATA_FILE):
        print("Write initial value to data file: " + str(INITIAL_VALUE))
        logger.info('Write initial value to data file: %s', str(INITIAL_VALUE))
        if not os.path.exists(os.path.dirname(DATA_FILE)):
            os.makedirs(os.path.dirname(DATA_FILE))
        f = open(DATA_FILE, "w+")
        f.write(str(INITIAL_VALUE))
        f.close()
    else:
        INITIAL_VALUE = readvalue()

    client = mqtt.Client(client_id="easymeter_s0", clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message
    # client.on_publish = on_publish
    client.on_disconnect = on_disconnect

    print("Connecting to mqtt broker")
    logger.info('Connecting to mqtt broker')
    client.username_pw_set("easymeter", password="easymeter")
    client.connect("rabbitmq.markusfriedrich.de", 1883, 60)
    publish(INITIAL_VALUE)

    print("Connecting to meter")
    logger.info('Connecting to meter')

    # Pin number from BCM numbering scheme. 27 BCM = Pin 13 on physical connector
    PIN_TO_SENSE = 27
    wiringpi.wiringPiSetupGpio()
    wiringpi.pinMode(PIN_TO_SENSE, wiringpi.GPIO.INPUT)
    wiringpi.pullUpDnControl(PIN_TO_SENSE, wiringpi.GPIO.PUD_DOWN)
    wiringpi.wiringPiISR(PIN_TO_SENSE, wiringpi.GPIO.INT_EDGE_RISING, gpio_callback)

    print('Startup complete')
    logger.info('Startup complete.')
    # Tell systemd that our service is ready
    sd.notify(sd.Notification.READY)

    try:
        while True:
            # Count only if any impulse was measured in ISR
            if global_last_imp > 0:
                global_deltai = global_impulse - global_last_imp
            else:
                global_deltai = 0
            global_last_imp = global_impulse

            if global_deltai > 0:
                # Energy
                global_kwh = global_deltai / STEPS
                # Avg. Power
                if global_deltat > 0.04:
                    global_kw = POWER_PER_IMP / global_deltat
                # persist
                INITIAL_VALUE += global_kwh
                writevalue(INITIAL_VALUE)
            else:
                global_kw = 0

            logger.info('last_i: %d, last_t: %.3f, imp: %d, kwh: %.1f, kw: %.1f', global_deltai, global_deltat, global_impulse, INITIAL_VALUE, global_kw)

            client.publish(MQTT_PREFIX + "kWh_value", INITIAL_VALUE)
            client.publish(MQTT_PREFIX + "kW_value", global_kw)

            # on paho client loop
            client.loop()

            # 10s
            time.sleep(10)
    except KeyboardInterrupt:
        print('Strg+c pressed. Bye')

