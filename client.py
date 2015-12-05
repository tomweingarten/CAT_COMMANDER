import threading
import signal
import sys
from nunchuck import nunchuck
import requests
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

# Constants
URL_BASE="http://your_url_here:port_number"

# Initialize the Wii Nunchuck
wii = nunchuck()

# Global variables to keep the nunchuck state
wii_joy_x = 0
wii_joy_y = 0
wii_c = False
wii_acc_x = 0
wii_acc_y = 0
wii_z = False

# Quit if Ctrl-C gets pressed
def signal_handler(signal, frame):
        print 'You pressed Ctrl+C! Exiting the CAT COMMANDER!'
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def watch_joystick():
  # If the joystick has moved, update the remote server
  global wii_joy_x
  global wii_joy_y
  global wii_c
  global wii_acc_x
  global wii_acc_y
  global wii_z
  while True:
    try:
      x,y = wii.joystick()
      # Scale the joystick measurements to servo motor positions
      x = wii.scale(x, 0, 255, 180, 0)
      y = wii.scale(y, 0, 255, 180, 0)
      if wii.button_c() and ((x != wii_joy_x) or (y != wii_joy_y)):
        # Update the current values
        wii_joy_x = x
        wii_joy_y = y
        # Update the remote server
        requests.get('%s/api/v1/laser_position/?id=0&x=%d&y=%d'%(URL_BASE,x,y))
      if wii.button_c() != wii_c:
        # Update the current values
        wii_c = wii.button_c()
        # Update the remote server
        value = 1 if wii_c else 0
        requests.get('%s/api/v1/laser/?id=0&status=%d'%(URL_BASE,value))
      x,y,z = wii.accelerometer()
      x = wii.scale(x, 0, 255, 180, 0)
      y = wii.scale(y, 0, 255, 0, 180)
      if wii.button_z() and ((x != wii_acc_x) or (y != wii_acc_y)):
        # Update the current values
        wii_acc_x = x
        wii_acc_y = y
        # Update the remote server
        requests.get('%s/api/v1/laser_position/?id=1&x=%d&y=%d'%(URL_BASE,x,y))
      if wii.button_z() != wii_z:
        # Update the current values
        wii_z = wii.button_z()
        # Update the remote server
        value = 1 if wii_z else 0
        requests.get('%s/api/v1/laser/?id=1&status=%d'%(URL_BASE,value))
    except Exception as e:
      # Catch the exception, but keep on going
      print "There was a problem connecting to the cat commander relay server"
      print e

# Set up a background thread to watch the joystick
joystick_thread = threading.Thread(target=watch_joystick)
joystick_thread.daemon = True
joystick_thread.start()

# Once every 30 seconds, update the tasks
while True:
  tasks = get_uncompleted_tasks()
  time.sleep(30)
