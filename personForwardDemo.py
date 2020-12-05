import os

'''
    人物方向判断推演
'''



image_size = (1920, 1080)

prevList = [("101", [100, 200, 300, 400]),
            ("102", [500, 600, 700, 800]),
            ("103", [900, 1000, 1100, 1200])]

trackList = [("101", [180, 150, 220, 300]),
            ("102", [550, 650, 750, 850]),
            ("104", [950, 1050, 1150, 1250])]

lastList = [("101", [600, 500, 700, 1500]),
            ("102", [600, 1000, 700, 1500]),
            ("104", [1250, 900, 1400, 1500]),
            ("105", [300, 400, 500, 600])]

list = []
list.append(prevList)
list.append(trackList)
list.append(lastList)

def judgeStatus(tracklist, personForwardDict, personBoxDict, personLocaDict, personIsCrossLine):
    # print("传入的参数: ")
    # print("personForwardDict:", personForwardDict)
    # print("personBoxDict:", personBoxDict)
    # print("personLocaDict:", personLocaDict)
    # print("personIsCrossLine:", personIsCrossLine)

    curr_person_id_list = []
    for track in tracklist:
        # person_id = track.track_id    # 人的id
        person_id = track[0]
        curr_person_id_list.append(person_id)
        # bbox = track.to_tlbr()  # 左上右下
        bbox = track[1]
        left, top, right, bottom = bbox
        centery = (top + bottom) / 2

        # 先加新人
        if person_id not in personForwardDict.keys():  # 如果该人第一次来
            personForwardDict[person_id] = "0"
            personBoxDict[person_id] = bbox
            personLocaDict[person_id] = "0" if centery < image_size[1] / 2 else "1"
            personIsCrossLine[person_id] = "0"    # 默认没过线
        else:
            prev_forward = personForwardDict[person_id]  # 当前人上一帧的方向
            prev_box = personBoxDict[person_id]  # 当前人上一帧的框
            prev_loca = personLocaDict[person_id]  # 当前人上一帧的位置

            prev_left, prev_top, prev_right, prev_bottom = prev_box
            prev_centery = (prev_top + prev_bottom) / 2
            if centery < prev_centery:  # 当前小于上一帧
                personForwardDict[person_id] = 1  # 方向向上
            else:
                personForwardDict[person_id] = 2  # 方向向下
            personBoxDict[person_id] = bbox
            currLoca = "0" if centery < image_size[1] / 2 else "1"
            personLocaDict[person_id] = currLoca
            if currLoca == prev_loca:    # 当前位置和上一帧位置比较，相同则没过线，不同则过线
                personIsCrossLine[person_id] = "0"
            else:
                personIsCrossLine[person_id] = "1"
    # 再删旧人
    del_pid_list = []
    for pid in personForwardDict.keys():  # 出域的人方向标记为3，下一轮删除
        if pid not in curr_person_id_list:
            personForwardDict[pid] = "3"  # 先标记
            del_pid_list.append(pid)

    # 再删除
    for pid in del_pid_list:
        del personForwardDict[pid]
        del personBoxDict[pid]
        del personLocaDict[pid]
        del personIsCrossLine[pid]
    return personForwardDict, personBoxDict, personLocaDict, personIsCrossLine


if __name__ == '__main__':
    personBoxDict = {}  # 每个人的人物框：{person_id: box左上右下}
    personForwardDict = {}  # 每个人的方向状态：{personid: 方向}，0无方向（新人）；1向上；2向下；3丢失（出域）
    personLocaDict = {}  # 每个人的位置：{personid: 位置}，0图像上半截；1图像下半截
    personIsCrossLine = {}  # 每个人是否过线：{personid: 是否过线}，0没过线；1过线

    for i in range(len(list)):
        currls = list[i]
        personForwardDict, personBoxDict, personLocaDict, personIsCrossLine = judgeStatus(currls, personForwardDict, personBoxDict, personLocaDict, personIsCrossLine)

        print("第%d轮：" % i)
        print("personForwardDict:", personForwardDict)
        print("personBoxDict:", personBoxDict)
        print("personLocaDict", personLocaDict)
        print("personIsCrossLine:", personIsCrossLine)

