from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, Response, send_from_directory
import time
from bluepy import btle
import logging
import server_settings

app = Flask(__name__)
app.config.from_object(__name__)
# WARNING: For some reason, setting Flask DEBUG=True causes btle to fail
app.config["PROPOGATE_EXCEPTIONS"] = True

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

def cors(response):
    # Allow AJAX interactions from other domains
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/api/v1/laser/')
def v1_laser():
    # Turn the laser on or off
    laser_id = request.args.get('id', 0, type=int)
    laser_status = request.args.get('status', 0, type=int)
    # Communicate the status to BTLE
    btle_write('laser %d %d\n'%(laser_id, laser_status));
    return cors(Response({"success": True}, status=200, mimetype='application/json'))


@app.route('/api/v1/laser_position/')
def v1_laser_position():
    # Set the laser position
    laser_id = request.args.get('id', 0, type=int)
    laser_x = request.args.get('x', 0, type=int)
    laser_y = request.args.get('y', 0, type=int)
    # Communicate the new position to BTLE
    btle_write('laser_position %d %d %d\n'%(laser_id, laser_x, laser_y));
    return cors(Response({"success": True}, status=200, mimetype='application/json'))


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
    if p and p.waitForNotifications(1.0):
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
    if p and p.waitForNotifications(1.0):
        global notification_data
        global visor_status
        visor_status = bool(notification_data)
        notification_data = False
        print visor_status
        return
    # There was some problem loading the data
    visor_status = False

def btle_write(data, retry=0):
    try:
        # write data in 10 character chunks
        length = 20
        payloads = [data[0+i:length+i] for i in range(0, len(data), length)]
        for payload in payloads:
            tx.write(payload)
    except:
        # Something went wrong, try to re-establish the connection
        btle_connect()
        # Retry the connection
        if retry < 3:
            btle_write(data, retry=retry+1)

def btle_connect():
    global p
    global tx_uuid
    global rx_uuid
    global tx
    global rx
    try:
        p = btle.Peripheral(server_settings.btle_address,"random")
    except btle.BTLEException as exc:
        print "Error connecting to BTLE device: " + exc.message
        return False
    tx_uuid = btle.UUID("6e400002-b5a3-f393-e0a9-e50e24dcca9e")
    rx_uuid = btle.UUID("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
    tx = p.getCharacteristics(uuid=tx_uuid)[0]
    rx = p.getCharacteristics(uuid=rx_uuid)[0]
    p.setDelegate( MyDelegate({}) )
    # Tell BTLE to accept notifications by sending 0x0100 to the CCCD
    p.writeCharacteristic(0x0023, '\x01\x00', False)
    return True

btle_connect()

# Run server as a standalone app
if __name__ == '__main__':
    print "Beginning server"
    app.run(host='0.0.0.0', port=80)
