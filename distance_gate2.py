# !/usr/bin/env python
# encoding: utf-8
import time
import math
import threading
import serial
# import sys
# sys.path.append("D:/workspace/workspace_python/evade_pytorch/")
from common.dbUtil import saveDistanceInfo2DB
from common.config import ip, serial_com2
from common.dateUtil import formatTimestamp

'''
    北醒激光雷达
'''

ser = serial.Serial(serial_com2)
ser.baudrate = 115200
count = 0
totalnum = 0
havePeopleNum = 0
noPeopleNum = 0
data = ser.read()
hexold = 0
hexnew= 0

this_gate = 2    # 当前所在闸机：2号闸机

def update():
    #print("test3")
    global count
    global totalnum
    global havePeopleNum,noPeopleNum
    global hexold,hexnew
    data=ser.read()
    hexnew = ord(data)
    distance = 0
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
                ms_time = formatTimestamp(time.time(), format='%Y%m%d_%H%M%S', ms=True)
                print("!!! 有人: %s %d" % (ms_time, distance))
                saveDistanceInfo2DB(ip=ip, gate_num=this_gate, distance=distance)
            else:
                noPeopleNum +=1
                # ms_time = formatTimestamp(time.time(), format='%Y%m%d_%H%M%S', ms=True)
                # print("    无人: %s %d" % (ms_time, distance))
    hexold = hexnew
    return distance


def Subfun():
    while True:
        update()


if __name__ == '__main__':
    t = threading.Thread(target=Subfun)
    t.start()
