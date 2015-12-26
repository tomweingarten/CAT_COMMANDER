// Arduino SPI Library (for Bluetooth)
#include <SPI.h>

// Ada BLE library
#include <Adafruit_BLE.h>
#include <Adafruit_BluefruitLE_SPI.h>

#include <Adafruit_Sensor.h>
#include <DHT_U.h>
#include <DHT.h>

// Pins
#define DHTPIN 2

//int visor_led_pin = 5; // Temporarily disabling this
// Pins 7-9 are used for Bluetooth LE (but 9 is optional RST)
int visor_servo_pin = 0;
// Pins 11-13 are used for Bluetooth LE
int visor_button_pin = A0;
int laser0_pin = A1;
int laser1_pin = A2;

// What type of DHT sensor are we using?

#define DHTTYPE DHT22

#include "BluefruitConfig.h"

// Adafruit Servo library
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Constants
int VISOR_UP = 0;
int VISOR_DOWN = 1;
#define SERVOMIN  150 // this is the 'minimum' pulse length count (out of 4096)
#define SERVOMAX  600 // this is the 'maximum' pulse length count (out of 4096)

// Globals
int state;
String ble_input = "";
// Accept up to 64 characters
char *ble_input_char = (char *)malloc(sizeof(char) * 64);

Adafruit_BluefruitLE_SPI ble(BLUEFRUIT_SPI_CS, BLUEFRUIT_SPI_IRQ, BLUEFRUIT_SPI_RST);
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();
DHT_Unified dht(DHTPIN, DHTTYPE);

void setup() {
  while (!Serial); // required for Flora & Micro (apparently)
  Serial.begin(115200);
  Serial.println("Arduino is go.\n\nCAT COMMANDER ACTIVATE.");
  
  // put your setup code here, to run once:
  pinMode(laser0_pin, OUTPUT);
  pinMode(laser1_pin, OUTPUT);
  pinMode(visor_button_pin, INPUT_PULLUP);

  // default to hiding the visor
  state = VISOR_DOWN;

  // Set the BLE name
  ble.begin(VERBOSE_MODE);
  ble.setMode(BLUEFRUIT_MODE_DATA);
  ble.sendCommandCheckOK(F("AT+GAPDEVNAME=Servo Command"));

  // Default laser state
  digitalWrite(laser1_pin, LOW);

  ble_input.reserve(128);

  // Start up the servo driver
  pwm.begin();
  pwm.setPWMFreq(60); // Analog servos run at ~60 Hz updates

  // Execute the initial state
  run_state();
}

void run_state() {
  // Do the right thing depending on the state
  if (state == VISOR_UP) {
    // Turn on the LED
    //analogWrite(visor_led_pin, 127);
    // Uncover the camera with the motor
    pwm.setPWM(visor_servo_pin, 0, SERVOMIN);
  } else {
    // Turn off the LED
    //analogWrite(visor_led_pin, 1);
    // Cover the camera with the motor
    pwm.setPWM(visor_servo_pin, 0, SERVOMAX);
  }
  
}

void loop() {
  // put your main code here, to run repeatedly:
  int val = digitalRead(visor_button_pin);
  if (val == LOW) {
    // Button is pressed - toggle the state
    if (state == VISOR_UP) {
      //ble.print("Visor button pressed: closing");
      state = VISOR_DOWN;
    } else {
      //ble.print("Visor button pressed: opening");
      state = VISOR_UP;
    }

    run_state();
    delay(500); // Prevent button bouncing
  }

  // Process any incoming data over bluetooth
  int message_complete = 0;
  while ( ble.available() )
  {
    // Keep reading characters until we hit a newline
    int c = ble.read();
    if (c == '\n') {
      // Use newlines to terminate commands
      message_complete = 1;
      break;
    }
    ble_input += String((const char)c);
  }
  // Attempt to understand BLE command incoming
  if (message_complete) {
    //Serial.println(ble_input);
    ble_input.toCharArray(ble_input_char, ble_input.length()+1);
    if (ble_input.startsWith("laser ")) {
      int laser_id;
      int laser_status;
      sscanf(ble_input_char, "laser %d %d", &laser_id, &laser_status);
      //Serial.println(laser_id);
      //Serial.println(laser_status);
      if (laser_id == 0) {
        laser_id = laser0_pin;
      }else if (laser_id == 1) {
        laser_id = laser1_pin;
      }
      if (laser_status){
        //Serial.println("Laser on");
        digitalWrite(laser_id, HIGH);
      }else{
        //Serial.println("Laser off");
        digitalWrite(laser_id, LOW);
      }
    } else if (ble_input.startsWith("laser_position ")) {
      //Serial.print("Setting laser position\n");
      int laser_id;
      int laser_x_pin;
      int laser_y_pin;
      uint16_t laser_x;
      uint16_t laser_y;
      sscanf(ble_input_char, "laser_position %d %d %d", &laser_id, &laser_x, &laser_y);
//      Serial.println(laser_id);
//      Serial.println(laser_x);
//      Serial.println(laser_y);
//      Serial.println("end of output");
      laser_x_pin = 1 + (laser_id * 2);
      laser_y_pin = laser_x_pin + 1;
      laser_x = map(laser_x, 0, 180, SERVOMIN, SERVOMAX);
      laser_y = map(laser_y, 0, 180, SERVOMIN, SERVOMAX);
//      Serial.println(laser_x_pin);
//      Serial.println(laser_x);
//      Serial.println(laser_y_pin);
//      Serial.println(laser_y);
      pwm.setPWM(laser_x_pin, 0, laser_x);
      pwm.setPWM(laser_y_pin, 0, laser_y);
    } else if (ble_input == "get temperature") {
      //Serial.print("Requesting temperature");
      sensors_event_t event;
      dht.temperature().getEvent(&event);
      // Return the current temperature as a string
      ble.print(String(celsius_to_fahrenheit(event.temperature)));
    } else if (ble_input == "get visor_status") {
      //Serial.print("Requesting visor status");
      // Return the current visor status as a string
      if (state == VISOR_UP) {
        ble.print("true");
      } else {
        ble.print("false");
      }
    } else {
      Serial.println("Did not recognize that input");
    }
    // Reset the input back to blank
    ble_input = "";
  }
  run_state();

  if (state == VISOR_UP) {
    // Display the current temperature
    sensors_event_t event;
    dht.temperature().getEvent(&event);
    //String temp_string = String(celsius_to_fahrenheit(event.temperature), 0);
  }
}

void send_status() {
  ble.print("{");
  if (state == VISOR_UP) {
    ble.print("\"visor\": true");
  } else {
    ble.print("\"visor\": false");
  }
  sensors_event_t event;
  dht.temperature().getEvent(&event);
  ble.print(",\"temperature\": "+String(celsius_to_fahrenheit(event.temperature)));
  dht.humidity().getEvent(&event);
  ble.print(",\"humidity\": "+String(event.relative_humidity));
  ble.print("}");
}

float celsius_to_fahrenheit(float temperature){
  return (temperature*9.0)/5.0+32.0;
}

