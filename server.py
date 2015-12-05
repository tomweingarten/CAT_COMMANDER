from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, Response
import time
from bluepy import btle
import logging

app = Flask(__name__)
app.config.from_object(__name__)
# WARNING: For some reason, setting Flask DEBUG=True causes btle to fail
app.config["PROPOGATE_EXCEPTIONS"] = True

# Set this to the address of your Bluetooth LE device
btle_address = "Your:Address:Here"

# Log to stdout
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

notification_data = False # Buffer to store data from BTLE. False if nothing yet read or data already read
temperature = None # None if not yet loaded
visor_status = None

debug = True

response_prefix = """
<html>
<head>
<title>CAT COMMANDER</title>
</head>
<body>
"""

response_suffix = """
</body>
"""

@app.route('/')
def main():
    response = response_prefix
    response += "<h1>WELCOME TO CAT COMMANDER</h1>"
    # Get data from Bluetooth
    load_temperature()
    load_visor_status()
    if temperature != None:
        response += "The temperature in the apartment is %lfF<br/>" % temperature
    else:
        response += "There was a problem loading the temperature from the Arduino<br/><br/>"
    if visor_status == True:
        response += "The visor is open"
    elif visor_status == False:
        response += "The visor is closed"
    else:
        response += "There was a problem loading the visor status from the Arduino<br/><br/>"
    response += response_suffix
    return response

@app.route('/api/v1/laser/')
def v1_laser():
    # Turn the laser on or off
    laser_id = request.args.get('id', 0, type=int)
    laser_status = request.args.get('status', 0, type=int)
    # Communicate the status to BTLE
    btle_write('laser %d %d\n'%(laser_id, laser_status));
    return Response({"success": True}, status=200, mimetype='application/json')


@app.route('/api/v1/laser_position/')
def v1_laser_position():
    # Set the laser position
    laser_id = request.args.get('id', 0, type=int)
    laser_x = request.args.get('x', 0, type=int)
    laser_y = request.args.get('y', 0, type=int)
    # Communicate the new position to BTLE
    btle_write('laser_position %d %d %d\n'%(laser_id, laser_x, laser_y));
    return Response({"success": True}, status=200, mimetype='application/json')


class MyDelegate(btle.DefaultDelegate):
    def __init__(self, params):
        btle.DefaultDelegate.__init__(self)
        if debug:
            print "Starting BTLE notification delegate"
    def handleNotification(self, cHandle, data):
        # We received some data!
        global notification_data
        notification_data = data
        if debug:
            print data
            print notification_data

def load_temperature():
    # Tell the BTLE we want to receive the temperature
    btle_write('get temperature\n');
    if p.waitForNotifications(1.0):
        global notification_data
        global temperature
        temperature = float(notification_data)
        notification_data = False
        print temperature
        return
    # There was some problem loading the data
    temperature = False

def load_visor_status():
    # Tell the BTLE we want to receive the status of the visor
    btle_write('get visor_status\n');
    if p.waitForNotifications(1.0):
        global notification_data
        global visor_status
        visor_status = bool(notification_data)
        notification_data = False
        print visor_status
        return
    # There was some problem loading the data
    visor_status = False

def btle_write(data):
    try:
        # write data in 10 character chunks
        length = 20
        payloads = [data[0+i:length+i] for i in range(0, len(data), length)]
        for payload in payloads:
            tx.write(payload)
    except:
        # Something went wrong, try to re-establish the connection
        btle_connect()

def btle_connect():
    global p
    global tx_uuid
    global rx_uuid
    global tx
    global rx
    p = btle.Peripheral(btle_address,"random")
    tx_uuid = btle.UUID("6e400002-b5a3-f393-e0a9-e50e24dcca9e")
    rx_uuid = btle.UUID("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
    tx = p.getCharacteristics(uuid=tx_uuid)[0]
    rx = p.getCharacteristics(uuid=rx_uuid)[0]
    p.setDelegate( MyDelegate({}) )
    # Tell BTLE to accept notifications by sending 0x0100 to the CCCD
    p.writeCharacteristic(0x0023, '\x01\x00', False)

btle_connect()

# Run server as a standalone app
if __name__ == '__main__':
    print "Beginning server"
    app.run(host='0.0.0.0')