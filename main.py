# PubNub info:
# Publish key: pub-c-150e9604-b132-4f9d-9d6f-2d504e0e2d4a
# Subscribe key: sub-c-0b00fc02-ca83-11ec-8ef5-82b465a2b170
# Secret key: sec-c-NjNmMzM5OTAtNjkyOS00NGZlLTljZTgtMGRhZjhlNzhjMjcy
# Maps API key: AIzaSyA9USGsAyxWyFaTXVtSTgWhW5Hts9RFPUM

import serial
import time
import string
import pynmea2
import smbus
import math
import sys
from pygsm import GsmModem
from time import sleep
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.exceptions import PubNubException
from pygtkcompat.generictreemodel import handle_exception


# SERVER CONFIGURATION STARTS

# Name of channel that Raspberry Pi tracker will use with PubNub
pnChannel = "raspi-tracker"

# PubNub configuration information
pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-0b00fc02-ca83-11ec-8ef5-82b465a2b170"
pnconfig.publish_key = "pub-c-150e9604-b132-4f9d-9d6f-2d504e0e2d4a"
pnconfig.ssl = False
pubnub = PubNub(pnconfig)
pubnub.subscribe().channels(pnChannel).execute()

# SERVER CONFIGURATION ENDS

#ACCELEROMETER CONFIGURATION STARTS

# MPU6050 Registers and their address
PWR_MGMT_1 = 0x6B
SMPLRT_DIV = 0x19
CONFIG = 0x1A
GYRO_CONFIG = 0x1B
INT_ENABLE = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H = 0x43
GYRO_YOUT_H = 0x45
GYRO_ZOUT_H = 0x47


def MPU_Init():
    # Write to sample rate register
    bus.write_byte_data(Device_Address, SMPLRT_DIV, 7)
    # Write to power management register
    bus.write_byte_data(Device_Address, PWR_MGMT_1, 1)
    # Write to Configuration register
    bus.write_byte_data(Device_Address, CONFIG, 0)
    # Write to Gyro configuration register
    bus.write_byte_data(Device_Address, GYRO_CONFIG, 24)
    # Write to interrupt enable register
    bus.write_byte_data(Device_Address, INT_ENABLE, 1)

def read_raw_data(addr):
    # Accelerometer and Gyroscope values are 16-bit
    high = bus.read_byte_data(Device_Address, addr)
    low = bus.read_byte_data(Device_Address, addr + 1)
    # Concatenate higher and lower values
    value = ((high << 8) | low)
    # Convert to signed value
    if (value > 32768):
        value = value - 65536
    return value

bus = smbus.SMBus(1)  # Alternatively, bus = smbus.SMBus(0) for older version boards
Device_Address = 0x68  # MPU6050 device address

#Initialize the MPU6050
MPU_Init()
print("Reading Data of Accelerometer")

#ACCELEROMETER CONFIGURATION ENDS#

#GPS/GSM CONFIGURATION STARTS#

# Switch GPS on
def SwitchGPSon():
    print("Switching GPS on ...")
    reply = gsm.command('AT+CGNSPWR=1')
    print(reply)

# Switch GPS off
def SwitchGPSoff():
    print("Switching GPS off ...")
    reply = gsm.command('AT+CGNSPWR=0')
    print(reply)

# Send GPS location
def SendGPSPosition():
    print("Getting GPS position ...")
    reply = gsm.command('AT+CGNSINF')
    list = reply[0].split(",")
    UTC = list[2][8:10] + ':' + list[2][10:12] + ':' + list[2][12:14]
    Latitude = list[3]
    Longitude = list[4]
    Altitude = list[5]
    print('Position: ' + UTC + ', ' + Latitude + ', ' + Longitude + ', ' + Altitude)
    # Send text to mobile
    Message = ' Position: ' + UTC + ', ' + str(Latitude) + ', ' + str(Longitude) + ', ' + str(
        Altitude) + ' http://maps.google.com/?q=' + str(Latitude) + ',' + str(Longitude)
    print("Sending to mobile " + MobileNumber + ": " + Message)
    gsm.send_sms(MobileNumber, Message)
    #
    try:
        envelope = pubnub.publish().channel(pnChannel).message({
            'lat': Latitude,
            'lng': Longitude
        }).sync()
        print("publish timetoken: %d" % envelope.result.timetoken)
    except PubNubException as e:
        handle_exception(e)
    #

# Set mobile number here
MobileNumber = "3059042757"
lastmessage = 'Stop'

# Start serial connection to GSM modem
print("Reading Data of GSM Modem")
gsm = GsmModem(port="/dev/serial0") #May need to set to serial1 depending on Raspberry Pi version
gsm.boot()

# Note down modem details for identification
print("Modem details:")
reply = gsm.hardware()
print("Manufacturer = " + reply['manufacturer'])
print("Model = " + reply['model'])

# Try and get the phone number
reply = gsm.command('AT+CNUM')
if len(reply) > 1:
    list = reply[0].split(",")
    phone = list[1].strip('\"')
    print("Phone number = " + phone)

# Clear old messages
gsm.query("AT+CMGD=70,4")

# Turn on GPS
SwitchGPSon()
print("Reading Data of GPS module")

#GPS/GSM CONFIGURATION ENDS#

#MAIN LOOP BEGINS

# Begin sending messages
print("Boot successful, waiting for messages ...")
while True:
    # Check for messages
    message = gsm.next_message()
    # When a new message appears,
    if message:
        print("loop 1")
        print(message)
        text = message.text
        # And that message is "Start",
        if text[0:5] == 'Start':
            print("Start sending Position ...")
            # Send an initial GPS location
            SendGPSPosition()
            lastmessage = 'Start'
            time.sleep(300)
        # And that message is "Stop",
        elif text[0:4] == 'Stop':
            print("Text was Stop. Stop sending")
            # Stop sending GPS location
            lastmessage = 'Stop'
    # If there is no new message,
    else:
        # And the most recent message was "Start",
        if lastmessage == 'Start':
            # Read Accelerometer raw value
            acc_x = read_raw_data(ACCEL_XOUT_H)
            acc_y = read_raw_data(ACCEL_YOUT_H)
            acc_z = read_raw_data(ACCEL_ZOUT_H)
            # Divide raw value by sensitivity scale factor
            Ax = acc_x / 16384.0
            Ay = acc_y / 16384.0
            Az = acc_z / 16384.0
            # Only send an update if acceleration is above 0.05g
            if(Ax < 0.05 and Ay < 0.05 and Az <0.05):
                print(lastmessage + ' loop2')
                SendGPSPosition()
                time.sleep(300)
        # Otherwise, do nothing
        else:
            time.sleep(10)

#MAIN LOOP ENDS