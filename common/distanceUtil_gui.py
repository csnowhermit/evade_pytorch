# !/usr/bin/env python
# encoding: utf-8
import time
import math
import threading
import serial
from tkinter import *

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
            timeText.configure(text=distance)
            if distance <= 140:
                havePeopleNum +=1
                Text4.configure(text="有人",fg="red")
            else:
                noPeopleNum +=1
                Text4.configure(text="无人",fg="blue")
    hexold = hexnew
    root.after(2,update)


root = Tk()
root.title("北醒雷达测试")
root.geometry('500x400')
theta = StringVar()

timeText = Label(root,text="",width=3,font=("Helvetica", 100),bg="white",justify=LEFT,anchor="e")
#txt1 = Label(root,text="距离",width=3,font=("Helvetica", 30),).grid(row=0,column=0,padx=20, pady=5,sticky=W,columnspan=2)
Text2 = Label(root, text="距离", font=("Helvetica", 20))
Text3 = Label(root, text="cm", font=("Helvetica", 20))
Text4 = Label(root, text="无人", font=("Helvetica", 80),fg="red")


#timeText.grid(row=0, column=0, padx=5, pady=5)
timeText.grid(row=0,column=0,padx=20, pady=5,sticky=W,columnspan=2)
Text2.grid(row=1, column=0, padx=5, pady=5)
Text3.grid(row=1, column=1, padx=5, pady=5)
Text4.grid(row=2, column=0, padx=20, pady=5,sticky=W,columnspan=2)

def Subfun():
    update()

t = threading.Thread(target=Subfun)
t.start()
mainloop()