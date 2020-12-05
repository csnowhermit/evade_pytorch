# !/usr/bin/env python
# encoding: utf-8
import time
import math
import threading
import serial

'''
    北醒激光雷达
'''

ser = serial.Serial('COM3')
ser.baudrate = 115200
count = 0
totalnum = 0
havePeopleNum = 0
noPeopleNum = 0
data = ser.read()
hexold = 0
hexnew= 0

def update():
    #print("test3")
    global count
    global totalnum
    global havePeopleNum,noPeopleNum
    global hexold,hexnew
    data=ser.read()
    hexnew = ord(data)
    if hexnew == 0x59 and hexold == 0x59:
        hexnew = 0
        hexold= 0
        ladar_data = ser.read(7)
        distance = ladar_data[0] + ladar_data[1]*256

        count += 1
        if count >= 10:
            count = 0
            totalnum +=1
            if distance <= 140:
                havePeopleNum +=1
                print("!!! 有人: %d" % distance)
            else:
                noPeopleNum +=1
                print("    无人: %d" % distance)
    hexold = hexnew




def Subfun():
    while True:
        update()

t = threading.Thread(target=Subfun)
t.start()
# mainloop()