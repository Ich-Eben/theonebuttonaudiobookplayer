#!/usr/bin/env python
#  Copyright (C) 2012 Michael Clemens
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import RPi.GPIO as GPIO
import os
import pyudev

from mpd import (MPDClient, CommandError)
from socket import error as SocketError
from time import sleep

# Configure MPD connection settings
HOST = 'localhost'
PORT = '6600'
CON_ID = {'host':HOST, 'port':PORT}

# Configure IO ports
BUTTON = 17
LED = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON, GPIO.IN)
GPIO.setup(LED, GPIO.OUT)

# USB key FS label
USBNAME = "16GB" # 16GB is the name of my thumb drive

## Some functions
def mpdConnect(client, con_id):
        """
        Simple wrapper to connect MPD.
        """
        try:
                client.disconnect()
                client.connect(**con_id)
        except SocketError:
                return False
        return True

def loadMusic(client, con_id, device):
        os.system("mount "+device+" /music/usb")
        os.system("/etc/init.d/mpd stop")
        os.system("rm /music/mp3/* -R")
        os.system("cp /music/usb/audiobooks/* /music/mp3/ -R")
        sleep(2)
        os.system("umount /music/usb")
        os.system("rm /music/mpd/tag_cache")
        sleep(2)
        os.system("/etc/init.d/mpd start")
        os.system("mpc clear")
        sleep(10)
        os.system("mpc ls | mpc add")
        sleep(20)
        os.system("/etc/init.d/mpd restart")
        sleep(10)

def flashLED(speed, time):
        for x in range(0, time):
                GPIO.output(LED, GPIO.LOW)
                sleep(speed)
                GPIO.output(LED, GPIO.HIGH)
                sleep(speed)

def updateLED(client):
        # adjust LED to actual state
        if client.status()["state"] == "play":
                GPIO.output(LED, GPIO.LOW)
        else:
                GPIO.output(LED, GPIO.HIGH)

def checkForUSBDevice(name):
        res = ""
        context = pyudev.Context()
        for device in context.list_devices(subsystem='block', DEVTYPE='partition'):
                if device.get('ID_FS_LABEL') == name:
                        res = device.device_node
        return res

def getTimes(client):
        try:
                timeEl,timeLe = client.status()["time"].split(":")
                timeEl = int(timeEl)
                timeLe = int(timeLe)
        except Exception as e:
                timeEl = 0
                timeLe = 0
        return timeEl, timeLe

def seekBack(client, time):
        timeEl, timeLe = getTimes(client)
        if timeEl > time or int(client.status()["song"]) <= 0:
                client.seekcur(-time)
        else:
                timez = time - timeEl
                while timez > 0:
                        client.previous()
                        timeEl, timeLe = getTimes(client)
                        if timeLe > timez:
                                client.seekcur(timeLe - timez)
                                break
                        else:
                                timez = timez - timeLe
                        if int(client.status()["song"]) <= 0:
                                break

def main():
        ## MPD object instance
        client = MPDClient()
        mpdConnect(client, CON_ID)

        client.setvol(96)

        status = client.status()
        print status

        timebuttonisstillpressed = 0

        flashLED(0.1, 5)
        updateLED(client)

        while True:
                device = checkForUSBDevice(USBNAME)
                if device != "":
                        # USB thumb drive has been inserted, new music will be copied
                        flashLED(0.1, 5)
                        client.disconnect()
                        loadMusic(client, CON_ID, device)
                        mpdConnect(client, CON_ID)
                        print client.status()
                        flashLED(0.1, 5)
                        # wait until thumb drive is umplugged again
                        while checkForUSBDevice(USBNAME) == device:
                                sleep(1.0)
                        flashLED(0.1, 5)
                if GPIO.input(BUTTON) == True:
                        if timebuttonisstillpressed == 0:
                                # button has been pressed, pause or unpause now
                                if mpdConnect(client, CON_ID):
                                        if client.status()["state"] == "pause":
                                                seekBack(client, 30)
                                                print "play"
                                                client.play()
                                        elif client.status()["state"] == "stop":
                                                print "play"
                                                client.play()
                                        else:
                                                print "pause"
                                                client.pause()
                                updateLED(client)
                                print client.status()
                        elif timebuttonisstillpressed > 4:
                                # go back one track if button is pressed > 4 secs
                                seekBack(client,10 * 60)
                                flashLED(0.1, 5)
                                timebuttonisstillpressed = 0
                                print client.status()
                        timebuttonisstillpressed = timebuttonisstillpressed + 0.1
                else:
                        timebuttonisstillpressed = 0

                sleep(0.1)

# Script starts here
if __name__ == "__main__":
    main()
