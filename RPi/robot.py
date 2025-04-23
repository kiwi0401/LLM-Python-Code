#!/usr/bin/env/python3
# File name   : robot.py
# Description : Robot interfaces.
import json
import time

import serial

ser = serial.Serial("/dev/ttyS0", 115200)
dataCMD = json.dumps({'var': "", 'val': 0, 'ip': ""})
upperGlobalIP = 'UPPER IP'

pitch, roll = 0, 0


def setUpperIP(ipInput):
    global upperGlobalIP
    upperGlobalIP = ipInput


def forward(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 1})
    ser.write(dataCMD.encode())
    print('robot-forward')


def backward(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 5})
    ser.write(dataCMD.encode())
    print('robot-backward')


def left(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 2})
    ser.write(dataCMD.encode())
    print('robot-left')


def right(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 4})
    ser.write(dataCMD.encode())
    print('robot-right')


def stopLR():
    dataCMD = json.dumps({'var': "move", 'val': 6})
    ser.write(dataCMD.encode())
    print('robot-stop')


def stopFB():
    dataCMD = json.dumps({'var': "move", 'val': 3})
    ser.write(dataCMD.encode())
    print('robot-stop')


def lookUp():
    dataCMD = json.dumps({'var': "ges", 'val': 1})
    ser.write(dataCMD.encode())
    print('robot-lookUp')


def lookDown():
    dataCMD = json.dumps({'var': "ges", 'val': 2})
    ser.write(dataCMD.encode())
    print('robot-lookDown')


def lookStopUD():
    dataCMD = json.dumps({'var': "ges", 'val': 3})
    ser.write(dataCMD.encode())
    print('robot-lookStopUD')


def lookLeft():
    dataCMD = json.dumps({'var': "ges", 'val': 4})
    ser.write(dataCMD.encode())
    print('robot-lookLeft')


def lookRight():
    dataCMD = json.dumps({'var': "ges", 'val': 5})
    ser.write(dataCMD.encode())
    print('robot-lookRight')


def lookStopLR():
    dataCMD = json.dumps({'var': "ges", 'val': 6})
    ser.write(dataCMD.encode())
    print('robot-lookStopLR')


def steadyMode():
    dataCMD = json.dumps({'var': "funcMode", 'val': 1})
    ser.write(dataCMD.encode())
    print('robot-steady')


def jump():
    dataCMD = json.dumps({'var': "funcMode", 'val': 4})
    ser.write(dataCMD.encode())
    print('robot-jump')


def handShake():
    dataCMD = json.dumps({'var': "funcMode", 'val': 3})
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
    dataCMD = json.dumps({'var': "light", 'val': colorNum})
    ser.write(dataCMD.encode())


def buzzerCtrl(buzzerCtrl, cmdInput):
    dataCMD = json.dumps({'var': "buzzer", 'val': buzzerCtrl})
    ser.write(dataCMD.encode())


def getAccelData():
    """
    Request accelerometer data from the robot and return parsed values
    Returns a dictionary with acc_x, acc_y, acc_z values
    """
    # Clear any existing data in the buffer
    ser.reset_input_buffer()

    # Send request command for accelerometer data
    ser.write("GET_ACCEL\n".encode())

    # Wait for response
    time.sleep(0.1)

    # Read response
    if ser.in_waiting:
        response = ser.readline().decode('utf-8').strip()
        try:
            # Parse JSON response
            accel_data = json.loads(response)
            return accel_data
        except json.JSONDecodeError:
            print("Error parsing accelerometer data")
            return None
    else:
        print("No response received from robot")
        return None


if __name__ == '__main__':
    # Example of how to get accelerometer data
    while True:
        accel = getAccelData()
        if accel:
            print("Accelerometer X: {}, Y: {}, Z: {}".format(accel['acc_x'], accel['acc_y'], accel['acc_z']))
        time.sleep(2)

    # jump()
    # while 1:
    #     time.sleep(1)
    #     pass'
