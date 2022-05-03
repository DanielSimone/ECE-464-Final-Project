# PubNub info:
# Publish key: pub-c-150e9604-b132-4f9d-9d6f-2d504e0e2d4a
# Subscribe key: sub-c-0b00fc02-ca83-11ec-8ef5-82b465a2b170
# Secret key: sec-c-NjNmMzM5OTAtNjkyOS00NGZlLTljZTgtMGRhZjhlNzhjMjcy
# Maps API key: AIzaSyA9USGsAyxWyFaTXVtSTgWhW5Hts9RFPUM

import serial
import time
import string
import pynmea2
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.exceptions import PubNubException
from pygtkcompat.generictreemodel import handle_exception

pnChannel = "raspi-tracker"

pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-0b00fc02-ca83-11ec-8ef5-82b465a2b170"
pnconfig.publish_key = "pub-c-150e9604-b132-4f9d-9d6f-2d504e0e2d4a"
pnconfig.ssl = False

pubnub = PubNub(pnconfig)
pubnub.subscribe().channels(pnChannel).execute()

while True:
    port = "/dev/ttyAMA0"
    ser = serial.Serial(port, baudrate=9600, timeout=0.5)
    dataout = pynmea2.NMEAStreamReader()
    newdata = ser.readline()

    if newdata[0:6] == "$GPRMC":
        newmsg = pynmea2.parse(newdata)
        lat = newmsg.latitude
        lng = newmsg.longitude
        try:
            envelope = pubnub.publish().channel(pnChannel).message({
                'lat': lat,
                'lng': lng
            }).sync()
            print("publish timetoken: %d" % envelope.result.timetoken)
        except PubNubException as e:
            handle_exception(e)
