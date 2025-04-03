#!/usr/bin/env/python3
# File name   : robot.py
# Description : Robot interfaces.
import time
import json
import serial
import sys

ser = serial.Serial("/dev/ttyS0",115200)
dataCMD = json.dumps({'var':"", 'val':0, 'ip':""})
upperGlobalIP = 'UPPER IP'


pitch, roll = 0, 0

# speed constant, in degrees per second and centimeters per second
turnRightConstant = 90
turnLeftConstant = 90
moveForwardConstant = 15
moveBackwardConstant = 20

def setUpperIP(ipInput):
	global upperGlobalIP
	upperGlobalIP = ipInput

def forward(speed=100):
	dataCMD = json.dumps({'var':"move", 'val':1})
	ser.write(dataCMD.encode())
	print('robot-forward')

def backward(speed=100):
	dataCMD = json.dumps({'var':"move", 'val':5})
	ser.write(dataCMD.encode())
	print('robot-backward')

def left(speed=100):
	dataCMD = json.dumps({'var':"move", 'val':2})
	ser.write(dataCMD.encode())
	print('robot-left')

def right(speed=100):
	dataCMD = json.dumps({'var':"move", 'val':4})
	ser.write(dataCMD.encode())
	print('robot-right')

def stopLR():
	dataCMD = json.dumps({'var':"move", 'val':6})
	ser.write(dataCMD.encode())
	print('robot-stop')

def stopFB():
	dataCMD = json.dumps({'var':"move", 'val':3})
	ser.write(dataCMD.encode())
	print('robot-stop')



def lookUp():
	dataCMD = json.dumps({'var':"ges", 'val':1})
	ser.write(dataCMD.encode())
	print('robot-lookUp')

def lookDown():
	dataCMD = json.dumps({'var':"ges", 'val':2})
	ser.write(dataCMD.encode())
	print('robot-lookDown')

def lookStopUD():
	dataCMD = json.dumps({'var':"ges", 'val':3})
	ser.write(dataCMD.encode())
	print('robot-lookStopUD')

def lookLeft():
	dataCMD = json.dumps({'var':"ges", 'val':4})
	ser.write(dataCMD.encode())
	print('robot-lookLeft')

def lookRight():
	dataCMD = json.dumps({'var':"ges", 'val':5})
	ser.write(dataCMD.encode())
	print('robot-lookRight')

def lookStopLR():
	dataCMD = json.dumps({'var':"ges", 'val':6})
	ser.write(dataCMD.encode())
	print('robot-lookStopLR')



def steadyMode():
	dataCMD = json.dumps({'var':"funcMode", 'val':1})
	ser.write(dataCMD.encode())
	print('robot-steady')

def jump():
	dataCMD = json.dumps({'var':"funcMode", 'val':4})
	ser.write(dataCMD.encode())
	print('robot-jump')

def handShake():
	dataCMD = json.dumps({'var':"funcMode", 'val':3})
	ser.write(dataCMD.encode())
	print('robot-handshake')

def lightCtrl(colorName, cmdInput):
	colorNum = 0
	if colorName == 'off':
		colorNum = 0
	elif colorName == 'blue':
		colorNum = 1
	elif colorName == 'red':
		colorNum = 2
	elif colorName == 'green':
		colorNum = 3
	elif colorName == 'yellow':
		colorNum = 4
	elif colorName == 'cyan':
		colorNum = 5
	elif colorName == 'magenta':
		colorNum = 6
	elif colorName == 'cyber':
		colorNum = 7
	dataCMD = json.dumps({'var':"light", 'val':colorNum})
	ser.write(dataCMD.encode())


def buzzerCtrl(buzzerCtrl, cmdInput):
	dataCMD = json.dumps({'var':"buzzer", 'val':buzzerCtrl})
	ser.write(dataCMD.encode())


# The following functions controls the angle and movement of the robot.

def turnRight(angle):
    turnRightTime = angle / turnRightConstant
    right()
    time.sleep(turnRightTime)
    stopLR()

def turnLeft(angle):
    angle = 0 - angle
    turnLeftTime = angle / turnLeftConstant
    left()
    time.sleep(turnLeftTime)
    stopLR()

def moveForward(distance):
    moveForwardTime = distance / moveForwardConstant
    forward()
    time.sleep(moveForwardTime)
    stopFB()

def moveBackward(distance):
    distance = 0 - distance
    moveBackwardTime = distance / moveBackwardConstant
    backward()
    time.sleep(moveBackwardTime)
    stopFB()

if __name__ == '__main__':
    # robotCtrl.moveStart(100, 'forward', 'no', 0)
    # time.sleep(3)
    # robotCtrl.moveStop()

    if len(sys.argv) < 3:
        print("Usage: python3 robot.py <angle> <distance>")
        sys.exit(1)

    # angle in degrees and distance in centimeters
    angle = int(sys.argv[1])
    distance = int(sys.argv[2])

    if angle > 0:
        turnRight(angle)
        time.sleep(1)
    elif angle < 0:
        turnLeft(angle)
        time.sleep(1)
    else:
        time.sleep(1)

    if distance > 0:
        moveForward(distance)
        time.sleep(1)
    elif distance < 0:
        moveBackward(distance)
        time.sleep(1)
    else:
        time.sleep(1)

    handShake()

    sys.exit()
    while 1:
        time.sleep(1)
        pass
