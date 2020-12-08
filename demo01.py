import os
import shutil

babyList = [
"10.6.8.181_20201204_214051.505.jpg",
"10.6.8.181_20201204_214051.754.jpg",
"10.6.8.181_20201204_214052.174.jpg",
"10.6.8.181_20201204_214052.429.jpg",
"10.6.8.181_20201204_214052.650.jpg",
"10.6.8.181_20201204_221147.980.jpg",
"10.6.8.181_20201204_221148.204.jpg",
"10.6.8.181_20201204_214320.554.jpg",
"10.6.8.181_20201204_214320.937.jpg",
"10.6.8.181_20201204_214321.161.jpg",
"10.6.8.181_20201204_214321.384.jpg",
"10.6.8.181_20201204_214321.658.jpg",
"10.6.8.181_20201204_214857.947.jpg",
"10.6.8.181_20201204_214858.187.jpg",
"10.6.8.181_20201204_214858.428.jpg",
"10.6.8.181_20201204_214858.665.jpg",
"10.6.8.181_20201204_214858.897.jpg",
"10.6.8.181_20201204_214859.144.jpg",
"10.6.8.181_20201204_214859.410.jpg",
"10.6.8.181_20201204_214859.697.jpg",
"10.6.8.181_20201204_214859.963.jpg",
"10.6.8.181_20201204_214900.190.jpg"
]

with open("D:/b.txt", 'r', encoding='utf-8') as fo:
    for line in fo.readlines():
        arr = line.strip("\n").split(" ")
        savefile = arr[0]
        box1 = arr[1]
        box2 = arr[2]

        left1, top1, right1, bottom1 = int(box1.split("_")[0]), int(box1.split("_")[1]), int(box1.split("_")[2]), int(box1.split("_")[3])
        center1y = (top1 + bottom1)/2

        left2, top2, right2, bottom2 = int(box2.split("_")[0]), int(box2.split("_")[1]), int(box2.split("_")[2]), int(box2.split("_")[3])
        center2y = (top2 + bottom2)/2

        distance = abs(center2y - center1y)

        if savefile in babyList:
            print(savefile, box1, box2, distance, "holdbaby,1920,1080")
        else:
            print(savefile, box1, box2, distance, "evade,1920,1080")