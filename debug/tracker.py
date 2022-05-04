import time
import math
import sys
from pygsm import GsmModem


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


# Set mobile number here
MobileNumber = "3059042757"
lastmessage = 'Stop'

# Start serial connection to GSM modem
print("Booting modem ...")
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
print("Deleting old messages ...")
gsm.query("AT+CMGD=70,4")

# Turn on GPS
SwitchGPSon()

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
            # Send the GPS location
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
            print(lastmessage + ' loop2')
            # Continue sending GPS location
            SendGPSPosition()
            time.sleep(300)
        # Otherwise, do nothing
        else:
            time.sleep(10)