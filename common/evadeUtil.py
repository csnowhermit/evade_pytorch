import os
import math
import traceback
import numpy as np
import pandas as pd
from collections import Counter
from common.config import up_distance_rate, down_distance_rate, log, adult_types, image_size, gateDistanceDict, through_gate_area
from common.ContextParam import getContextParam
from common.entity import TrackContent
from common.dbUtil import getDistanceByTime
from common.dateUtil import datetime_add

'''
    逃票检测工具类
'''

# cap与location的绑定关系
capLocationList = getContextParam()
passway_area_list = [[capLocation.passway_area.left,
                      capLocation.passway_area.top,
                      capLocation.passway_area.right,
                      capLocation.passway_area.bottom] for capLocation in capLocationList]
passway_default_direct_list = [capLocation.default_direct for capLocation in capLocationList]    # 闸机的方向：0出站，1进站
# print("passway_default_direct_list:", passway_default_direct_list)    # 实时计算拿默认方向，批处理用人相对位置结合cap_location.displacement字段微调
gate_area_list = [[capLocation.gate_area.left,
                   capLocation.gate_area.top,
                   capLocation.gate_area.right,
                   capLocation.gate_area.bottom] for capLocation in capLocationList]    # 闸机门区域序列
gate_light_area_list = [[capLocation.gate_light_area.left,
                         capLocation.gate_light_area.top,
                         capLocation.gate_light_area.right,
                         capLocation.gate_light_area.bottom] for capLocation in capLocationList]    # 闸机灯区域序列
gate_default_displacement_list = [capLocation.displacement for capLocation in capLocationList]    # 闸机位移方向列表

# print("passway_area_list:", passway_area_list)
# print("gate_area_list:", gate_area_list)
# print("gate_light_area_list:", gate_light_area_list)
# print("gate_default_displacement_list:", gate_default_displacement_list)

'''
    拿到指定通道的默认方向
    :param gate_num int类型，闸机编号
    :return 返回该通道的默认方向：0出站，1进站
'''
def getDefaultDirection(gate_num):
    for capLocation in capLocationList:
        if capLocation.gate_num == str(gate_num):
            return capLocation.default_direct

'''
    逃票判定
    :param tracks 人的tracks，所有被追踪的人
    :param other_classes 其他的类别
    :param other_boxs 其他类别框，上左下右
    :param other_scores 其他类别的得分值
    :param height 图像的高
    :param personForwardDict {personid: 方向}
    :param personBoxDict {person_id: box左上右下}
    :param personLocaDict {personid: 位置}
    :param personIsCrossLine {personid: 是否过线}
    :param curr_time 当前时间
    :return flag, TrackContentList 通行状态，新的追踪人的内容
'''
def evade_vote(tracks, other_classes, other_boxs, other_scores, height, personForwardDict, personBoxDict,
                                                    personLocaDict, personIsCrossLine, curr_time):
    TrackContentList = []    # 追踪人的内容，新增闸机编号和通过状态，过滤掉不在有效闸机通道的人员
    flag = "NORMAL"    # 默认该帧图片的通行状态为NORMAL，遇到有逃票时改为WARNING
    up_distance_threshold = height * up_distance_rate
    down_distance_threshold = height * down_distance_rate
    print("人间距上限: %.3f, 下限: %.3f" % (up_distance_threshold, down_distance_threshold))
    log.logger.info("人间距上限: %.3f, 下限: %.3f" % (up_distance_threshold, down_distance_threshold))

    bboxes = [[int(track.to_tlbr()[0]),
               int(track.to_tlbr()[1]),
               int(track.to_tlbr()[2]),
               int(track.to_tlbr()[3])] for track in tracks]  # 所有人的人物框
    classes = [track.classes for track in tracks]    # 所有人的类别
    personidArr = [track.track_id for track in tracks]    # 所有人的id

    print("人物框序列bboxes：%s" % bboxes)
    print("人物类型序列classes：%s" % classes)
    print("人物ID序列personidArr：%s" % personidArr)
    log.logger.info("人物框序列bboxes：%s" % bboxes)
    log.logger.info("人物类型序列classes：%s" % classes)
    log.logger.info("人物ID序列personidArr：%s" % personidArr)

    print("personForwardDict: %s" % personForwardDict)
    print("personBoxDict: %s" % personBoxDict)
    print("personLocaDict: %s" % personLocaDict)
    print("personIsCrossLine: %s" % personIsCrossLine)
    log.logger.info("personForwardDict: %s" % personForwardDict)
    log.logger.info("personBoxDict: %s" % personBoxDict)
    log.logger.info("personLocaDict: %s" % personLocaDict)
    log.logger.info("personIsCrossLine: %s" % personIsCrossLine)

    if len(bboxes) < 1:
        flag = "NOBODY"
        log.logger.warn(flag)
        return flag, TrackContentList    # 没人的话返回标识“NOBODY”，不用走以下流程


    ## 1.先处理其他框：闸机门、闸机灯
    # 1.1、先转框格式
    other_bboxes = [[int(obox[1]),
                     int(obox[0]),
                     int(obox[3]),
                     int(obox[2])] for obox in other_boxs]    # 处理其他框：上左下右--->左上右下

    # 1.2、分离出闸机门和闸机灯
    # 检测到的闸机位置
    real_gate_area_list = [other_box for (other_cls, other_box) in zip(other_classes, other_bboxes) if other_cls in ['cloudGate', 'normalGate']]
    # 检测到的灯类别及位置
    real_gate_light_cls_list = [other_cls for other_cls in other_classes if
                                other_cls in ['redLight', 'greenLight', 'yellowLight']]
    real_gate_light_area_list = [other_box for (other_cls, other_box) in zip(other_classes, other_bboxes) if
                                 other_cls in ['redLight', 'greenLight', 'yellowLight']]


    # 1.3、计算检测到的闸机位置与真实闸机位置的iou
    gate_status_list = getGateStatusList(real_gate_area_list)    # 从左到右，按序标识闸机开关情况
    print("gate_status_list:", gate_status_list)    # gate_status_list: ['closed', 'closed', 'open']
    log.logger.info("闸机开关状态 gate_status_list: %s" % (gate_status_list))

    # 1.4、绑定闸机灯与通道的关系
    gate_light_status_list = getGateLightStatusList(real_gate_light_cls_list, real_gate_light_area_list)
    print("gate_light_status_list:", gate_light_status_list)    # gate_light_status_list: ['NoLight', 'whiteLight', 'greenLight']
    log.logger.info("灯状态 gate_light_status_list: %s" % (gate_light_status_list))

    ################################################
    ## 至此，闸机门和闸机灯状态是全局的（即，只要有一个通道有人，则所有门、灯都有状态）
    ## 解决办法：
    ## 方法1：把没人的通道和灯删掉（此法不可行，原因：当一个通道同时出现两人时，此法得到的gate_status_list和gate_light_status_list比真实数量少1）
    ## 方法2：构建TrackContent时，通过gate_num，直接从gate_status_list和gate_light_status_list中拿对应通道的状态

    ## 2.再处理人：尾随逃票情况
    # 判断各自在哪个通道内
    which_gateList = isin_which_gate(bboxes)    # which_gateList，有人的闸机序列，每个人的框和各自的闸机序列一一对应
    pass_status_list = [0] * len(bboxes)  # 每个人的通行状态
    print("有人的闸机序列 which_gateList:", which_gateList)    # which_gateList: [2]，
    log.logger.info("有人的闸机序列 which_gateList: %s" % (which_gateList))
    # which_gateList = [1, 2, 1, 2]    # 写死，测试用

    ## 方法1：已废弃
    # gate_status_list_new = []    # 闸机开关状态：只保留有人的通道
    # gate_light_status_list_new = []    # 闸机灯状态：只保留有人通道的灯

    # for i in range(len(passway_area_list)):
    #     if i in which_gateList:
    #         gate_status_list_new.append(gate_status_list[i])
    #         gate_light_status_list_new.append(gate_light_status_list[i])

    # 2.2、判断各自通道内的人数

    # # 2.1、先做钻闸机的判定
    # for i in range(len(bboxes)):
    #     box = bboxes[i]    # 当前人
    #     gate_num = which_gateList[i]    # 当前人所在通道
    #     light_status = gate_light_status_list[gate_num]    # 当前通道的指示灯
    #     gate_status = gate_status_list[gate_num]    # 当前通道闸机门的状态
    #     person_cls = classes[i]    # 当前人的类别
    #     person_id = personidArr[i]    # 当前人的id
    #     isCrossed = personIsCrossLine[person_id]    # 当前人是否过线：0没过线；1过线
    #
    #     if gate_status == "closed":    # 当闸机关
    #         if person_cls == "adult":    # 且为大人（小孩站着过都不算逃票，更何况钻过去了）
    #             if light_status == "redLight":    # 且亮红灯
    #                 if isin_throughArea(box) is True:    # 且在钻闸机判定区间内
    #                     if isCrossed == "1":    # 且过线，则认为是钻闸机的逃票
    #                         flag = "WARNING"    # 检测到有逃票，标记位WARNING
    #                         pass_status_list[i] = 4    # 4代表 钻闸机逃票

    # 2.2、尾随逃票情况
    # 2.2.1、分组统计各通道内人数
    gateCounter = Counter(which_gateList)
    print("gateCounter:", gateCounter)
    log.logger.info("各通道内人数 gateCounter: %s" % (gateCounter))    # Counter({1: 1, 2: 1, -1: 1})

    # 2.2.2、找出同一通道出现多人的序列
    multi_personList = []    # 同时出现多人的闸机序列
    for gate_num in gateCounter.keys():
        if gate_num == -1:
            continue    # 通道编号为-1，说明不在有效通道范围内，这些人不做逃票判定
        if gateCounter[gate_num] > 1:
            multi_personList.append(gate_num)    # 拿到几号闸机同时出现多人，后续做尾随逃票判定用

    # 2.2.3、同一通道出现多人的情况
    if len(multi_personList) > 0:    # 否则拿出各通道的人数，计算距离
        passwayPersonDict = {}    # <通道编号，通道内的人员list>
        for i in range(len(which_gateList)):    # 逐个通道获取各通道内的人的序号：
            if which_gateList[i] in multi_personList:
                if which_gateList[i] in passwayPersonDict.keys():
                    tmp = passwayPersonDict.get(which_gateList[i])
                    tmp.append(i)
                    passwayPersonDict[which_gateList[i]] = tmp
                else:
                    passwayPersonDict[which_gateList[i]] = [i]
        print("通道-人对应关系 passwayPersonDict:", passwayPersonDict)    # passwayPersonDict: {2: [0, 1]}，表示2号通道出现了0号人和1号人
        log.logger.info("通道-人对应关系 passwayPersonDict: %s" % (passwayPersonDict))

        for passway in passwayPersonDict.keys():    # 逐个处理每一个通道的多人情况
            personList = passwayPersonDict[passway]    # 拿到该通道内的所有人在bboxes中的序列，passway为通道编号
            default_displacement = gate_default_displacement_list[passway]    # 该通道的画面位移，默认通过该通道是往上还是往下

            suspicion_evade_boxes = [bboxes[person_index] for person_index in personList]  # 同一通道里的所有人框
            suspicion_evade_classes = [classes[person_index] for person_index in personList]    # 同一通道里的所有人类别
            suspicion_evade_personIds = [personidArr[person_index] for person_index in personList]  # 同一通道里的所有人id

            print("通道 %s：人物框：%s，人物类别：%s, 人物ID：%s" % (passway, suspicion_evade_boxes, suspicion_evade_classes, suspicion_evade_personIds))
            log.logger.info("通道 %s：人物框：%s，人物类别：%s, 人物ID：%s" % (passway, suspicion_evade_boxes, suspicion_evade_classes, suspicion_evade_personIds))
            ## 2.3、计算两两之间的距离，通过次距离判断是否属于逃票，center跟suspicion_evade_boxes平级，只是保存坐标点位不同
            center = [[(abs(left) + abs(right)) / 2,
                       (abs(top) + abs(bottom)) / 2] for (left, top, right, bottom) in suspicion_evade_boxes]

            evade_index_list = []       # 涉嫌逃票的序号：在原始bboxes中的序号
            delivery_index_list = []    # 隔闸机递东西的序号：在原始bboxes中的序号
            block_index_list = []       # 阻碍通行：闸机门关，多人在闸机同一侧

            for i in range(len(center)):    # 每个通道，两两人之间计算距离（i，j表示人在每个通道内的序列）
                for j in range(i + 1, len(center)):
                    person1x, person1y = center[i][0], center[i][1]
                    person2x, person2y = center[j][0], center[j][1]
                    # distance = math.sqrt(((person1x - person2x) ** 2) +
                    #                      ((person1y - person2y) ** 2))
                    distance = abs(person1y - person2y)    # 只算y方向上的，取绝对值

                    print("person1: %s %s, person2: %s %s, distance: %f" % (
                        suspicion_evade_classes[i], center[i], suspicion_evade_classes[j], center[j], distance))
                    log.logger.info("person1: %s %s, person2: %s %s, distance: %f" % (
                        suspicion_evade_classes[i], center[i], suspicion_evade_classes[j], center[j], distance))

                    if distance >= down_distance_threshold and distance <= up_distance_threshold:  # 如果距离满足条件

                        # 第i个人，第j个人
                        if suspicion_evade_classes[i] in adult_types and suspicion_evade_classes[j] in adult_types:    # 只有当两个人都是大人时

                            # 这时还需加入闸机门的判断：如果闸机门关（不存在过线的情况了），且两人在闸机门两侧，说明在递东西，pass_status置为2，不属于逃票
                            tag = isDelivery(person1y, person2y, gate_status_list[passway], gate_area_list[passway])
                            if tag == "Delivery":
                                # 隔闸机递东西
                                suspicion1 = suspicion_evade_boxes[center.index(center[i])]  # 递东西1
                                suspicion2 = suspicion_evade_boxes[center.index(center[j])]  # 递东西2
                                print("通道 %s: %s %s %s %s 递东西, distance: %f" % (
                                    passway, suspicion_evade_classes[i], suspicion1, suspicion_evade_classes[j],suspicion2, distance))  # [0, 0, 1, 2] [1, 1, 2, 2] 递东西
                                log.logger.warn("通道 %s: %s %s %s %s 递东西, distance: %f" % (
                                    passway, suspicion_evade_classes[i], suspicion1, suspicion_evade_classes[j],suspicion2, distance))

                                index1 = bboxes.index(suspicion1)
                                index2 = bboxes.index(suspicion2)
                                print("递东西-这两人真实全局序号：", index1, index2)  # 这两人真实序号： 0 2
                                log.logger.warn("递东西-这两人真实全局序号: %d %d" % (index1, index2))
                                delivery_index_list.append(index1)
                                delivery_index_list.append(index2)
                            elif tag == "block":
                                # 阻碍通行
                                suspicion1 = suspicion_evade_boxes[center.index(center[i])]  # 阻碍通行1
                                suspicion2 = suspicion_evade_boxes[center.index(center[j])]  # 阻碍通行2
                                print("通道 %s: %s %s %s %s 涉嫌阻碍通行, distance: %f" % (
                                    passway, suspicion_evade_classes[i], suspicion1, suspicion_evade_classes[j], suspicion2, distance))  # [0, 0, 1, 2] [1, 1, 2, 2] 涉嫌阻碍通行
                                log.logger.warn("通道 %s: %s %s %s %s 涉嫌阻碍通行, distance: %f" % (
                                    passway, suspicion_evade_classes[i], suspicion1, suspicion_evade_classes[j], suspicion2, distance))

                                index1 = bboxes.index(suspicion1)
                                index2 = bboxes.index(suspicion2)
                                print("涉嫌阻碍通行-这两人真实全局序号：", index1, index2)  # 这两人真实序号： 0 2
                                log.logger.warn("涉嫌阻碍通行-这两人真实全局序号: %d %d" % (index1, index2))
                                block_index_list.append(index1)
                                block_index_list.append(index2)
                            else:    # 这里是涉嫌逃票
                                suspicion1 = suspicion_evade_boxes[center.index(center[i])], suspicion_evade_personIds[center.index(center[i])]  # 嫌疑人1的box，id
                                suspicion2 = suspicion_evade_boxes[center.index(center[j])], suspicion_evade_personIds[center.index(center[j])]  # 嫌疑人2的box，id

                                index1 = bboxes.index(suspicion1[0])    # 涉嫌逃票的两人的全局序号
                                index2 = bboxes.index(suspicion2[0])

                                # 通道 2: adult [1632, 498, 1981, 758] adult [1634, 18, 1876, 158] 涉嫌逃票, distance: 540.000000
                                fmtStr = '''
                                            通道 %s: \n
                                            \t\t 类型: %s 人物: %s \n
                                            \t\t 类型: %s 人物: %s 涉嫌逃票 distance: %f \n
                                            \t\t 这两人真实全局序号: %d %d
                                        ''' % (passway,
                                               suspicion_evade_classes[i], str(suspicion1),
                                               suspicion_evade_classes[j], str(suspicion2), distance,
                                               index1, index2)
                                print(fmtStr)
                                log.logger.info(fmtStr)

                                person1_forward = personForwardDict[suspicion_evade_personIds[i]]    # 第1个人的方向
                                person2_forward = personForwardDict[suspicion_evade_personIds[j]]    # 第2个人的方向

                                # 1.如果两人方向一致，或任意一人是新来的
                                if person1_forward == person2_forward or person1_forward == "0" or person2_forward == "0":
                                    # 2.且后者过线，才认为是逃票
                                    # debug,
                                    # evade_following: 205.0
                                    # center: [[1726.5, 205.0], [1664.0, 703.0]]
                                    if default_displacement == "down":  # 向下走的，y轴坐标小的为尾随
                                        evade_following_y = min(center[i][1], center[j][1])  # 这里是中心点坐标
                                    else:
                                        evade_following_y = max(center[i][1], center[j][1])

                                    evade_following = [(center[i], i) for i in range(len(center)) if center[i][1] == evade_following_y][0]
                                    print("evade_following:", type(evade_following), evade_following, evade_following_y)
                                    print("center:", type(center), center)
                                    # 尾随的人的box和id
                                    suspicion_evade = suspicion_evade_boxes[center.index(evade_following[0])], suspicion_evade_personIds[center.index(evade_following[0])]

                                    # 被尾随的
                                    be_tailed = suspicion2 if suspicion_evade[1] == suspicion1[1] else suspicion1

                                    # # 尾随人过线判断：该逻辑不能用。原因：当逃票者过线时，被尾随者已经走出通道，这时通道内仍只有一个人（逃票者）
                                    # if personIsCrossLine[suspicion_evade[1]] == "1":    # 尾随人过线，是逃票
                                    if gate_light_status_list[passway] == "redLight":    # 此处用红灯预警替代
                                        # 这是再加身高的判断因素
                                        distance = getNearestDistance(passway, curr_time)    # 此距离为设备到测得物体的距离
                                        # person_height = total_height - distance    # 通过的人的身高
                                        if distance < gateDistanceDict[passway] or distance == 0:    # 距离比全程小（说明有物体挡住了），说明是大人（小孩挡不住距离）
                                            print("逃票详情：")
                                            print("逃票者：%s" % str(suspicion_evade))
                                            print("被尾随：%s" % str(be_tailed))
                                            log.logger.info("逃票详情：")
                                            log.logger.info("逃票者：%s" % str(suspicion_evade))
                                            log.logger.info("被尾随：%s" % str(be_tailed))

                                            evade_index_list.append(
                                                bboxes.index(suspicion_evade[0]))  # 只有逃票者会被记，被尾随的不会被记录

                                            flag = "WARNING"  # 检出有人逃票，该标识为WARNING
                                            log.logger.warn("检测到涉嫌逃票: %s" % flag)
                                        else:
                                            print("身高不足以购票: %f, 不认为是逃票" % (distance))
                                            log.logger.info("身高不足以购票: %f, 不认为是逃票" % (distance))
                                    else:
                                        print("尾随者 %s 未过线，不认为逃票" % (str(suspicion_evade)))
                                else:
                                    print("两人方向不一致，不认为逃票：第%d人方向：%s，第%d人方向：%s" % (i, person1_forward,
                                                                                                             j, person2_forward))

            # 更新每个人的通行状态
            for i in range(len(evade_index_list)):    # evade_index_list[i]为人在bboxes中的真实序号
                pass_status_list[evade_index_list[i]] = 1    # 更新通过状态为 1涉嫌逃票
            for i in range(len(delivery_index_list)):
                pass_status_list[delivery_index_list[i]] = 2    # 更新通过状态为 2 递东西
            for i in range(len(block_index_list)):
                pass_status_list[block_index_list[i]] = 3    # 更新通行状态为 3 阻碍通行
            print("更新后的通行状态: %s" % (pass_status_list))
            log.logger.info("更新后的通行状态: %s" % (pass_status_list))


    ## 4.更新每个人的track内容：新增：闸机编号、通过状态、闸机门状态、闸机灯状态
    for (track, which_gate, pass_status) in zip(tracks, which_gateList, pass_status_list):
        trackContent = TrackContent(gate_num=which_gate,    # 闸机编号
                                    pass_status=pass_status,
                                    cls=track.classes,    # 人物类别：大人/小孩
                                    score=track.score,
                                    track_id=track.track_id,
                                    state=track.state,
                                    bbox=Box2Line(track.to_tlbr()),
                                    direction=passway_default_direct_list[which_gate],    # 实时视图用默认方向，后续离线全局视图微调
                                    gate_status=gate_status_list[which_gate],    # 闸机门状态：通过闸机编号拿到
                                    gate_light_status=gate_light_status_list[which_gate])    # 闸机灯状态：通过闸机编号拿到
        TrackContentList.append(trackContent)
    return flag, TrackContentList


'''
    逃票判定：两人距离&尾随者是否过线同时判定
    :param tracks 人的tracks，所有被追踪的人
    :param other_classes 其他的类别
    :param other_boxs 其他类别框，上左下右
    :param other_scores 其他类别的得分值
    :param height 图像的高
    :param personForwardDict {personid: 方向}
    :param personBoxDict {person_id: box左上右下}
    :param personLocaDict {personid: 位置}
    :param personIsCrossLine {personid: 是否过线}
    :param curr_time 当前时间
    :param following_list 尾随者list，(box, id)
    :return flag, TrackContentList 通行状态，新的追踪人的内容
'''
def evade4new(tracks, other_classes, other_boxs, other_scores, height, personForwardDict, personBoxDict,
                                                    personLocaDict, personIsCrossLine, curr_time, following_list):
    TrackContentList = []    # 追踪人的内容，新增闸机编号和通过状态，过滤掉不在有效闸机通道的人员
    flag = "NORMAL"    # 默认该帧图片的通行状态为NORMAL，遇到有逃票时改为WARNING
    up_distance_threshold = height * up_distance_rate
    down_distance_threshold = height * down_distance_rate
    print("人间距上限: %.3f, 下限: %.3f" % (up_distance_threshold, down_distance_threshold))
    log.logger.info("人间距上限: %.3f, 下限: %.3f" % (up_distance_threshold, down_distance_threshold))

    bboxes = [[int(track.to_tlbr()[0]),
               int(track.to_tlbr()[1]),
               int(track.to_tlbr()[2]),
               int(track.to_tlbr()[3])] for track in tracks]  # 所有人的人物框
    classes = [track.classes for track in tracks]    # 所有人的类别
    personidArr = [track.track_id for track in tracks]    # 所有人的id

    print("人物框序列bboxes：%s" % bboxes)
    print("人物类型序列classes：%s" % classes)
    print("人物ID序列personidArr：%s" % personidArr)
    log.logger.info("人物框序列bboxes：%s" % bboxes)
    log.logger.info("人物类型序列classes：%s" % classes)
    log.logger.info("人物ID序列personidArr：%s" % personidArr)

    print("personForwardDict: %s" % personForwardDict)
    print("personBoxDict: %s" % personBoxDict)
    print("personLocaDict: %s" % personLocaDict)
    print("personIsCrossLine: %s" % personIsCrossLine)
    log.logger.info("personForwardDict: %s" % personForwardDict)
    log.logger.info("personBoxDict: %s" % personBoxDict)
    log.logger.info("personLocaDict: %s" % personLocaDict)
    log.logger.info("personIsCrossLine: %s" % personIsCrossLine)

    if len(bboxes) < 1:
        flag = "NOBODY"
        log.logger.warn(flag)
        return flag, TrackContentList, following_list    # 没人的话返回标识“NOBODY”，不用走以下流程


    ## 1.先处理其他框：闸机门、闸机灯
    # 1.1、先转框格式
    other_bboxes = [[int(obox[1]),
                     int(obox[0]),
                     int(obox[3]),
                     int(obox[2])] for obox in other_boxs]    # 处理其他框：上左下右--->左上右下

    # 1.2、分离出闸机门和闸机灯
    # 检测到的闸机位置
    real_gate_area_list = [other_box for (other_cls, other_box) in zip(other_classes, other_bboxes) if other_cls in ['cloudGate', 'normalGate']]
    # 检测到的灯类别及位置
    real_gate_light_cls_list = [other_cls for other_cls in other_classes if
                                other_cls in ['redLight', 'greenLight', 'yellowLight']]
    real_gate_light_area_list = [other_box for (other_cls, other_box) in zip(other_classes, other_bboxes) if
                                 other_cls in ['redLight', 'greenLight', 'yellowLight']]


    # 1.3、计算检测到的闸机位置与真实闸机位置的iou
    gate_status_list = getGateStatusList(real_gate_area_list)    # 从左到右，按序标识闸机开关情况
    print("gate_status_list:", gate_status_list)    # gate_status_list: ['closed', 'closed', 'open']
    log.logger.info("闸机开关状态 gate_status_list: %s" % (gate_status_list))

    # 1.4、绑定闸机灯与通道的关系
    gate_light_status_list = getGateLightStatusList(real_gate_light_cls_list, real_gate_light_area_list)
    print("gate_light_status_list:", gate_light_status_list)    # gate_light_status_list: ['NoLight', 'whiteLight', 'greenLight']
    log.logger.info("灯状态 gate_light_status_list: %s" % (gate_light_status_list))

    ################################################
    ## 至此，闸机门和闸机灯状态是全局的（即，只要有一个通道有人，则所有门、灯都有状态）
    ## 解决办法：
    ## 方法1：把没人的通道和灯删掉（此法不可行，原因：当一个通道同时出现两人时，此法得到的gate_status_list和gate_light_status_list比真实数量少1）
    ## 方法2：构建TrackContent时，通过gate_num，直接从gate_status_list和gate_light_status_list中拿对应通道的状态

    ## 2.再处理人：尾随逃票情况
    # 判断各自在哪个通道内
    which_gateList = isin_which_gate(bboxes)    # which_gateList，有人的闸机序列，每个人的框和各自的闸机序列一一对应
    pass_status_list = [0] * len(bboxes)  # 每个人的通行状态
    pass_distance_list = [0] * len(bboxes)    # 涉嫌逃票的两个人，人头中心点的距离
    print("有人的闸机序列 which_gateList:", which_gateList)    # which_gateList: [2]，
    log.logger.info("有人的闸机序列 which_gateList: %s" % (which_gateList))
    # which_gateList = [1, 2, 1, 2]    # 写死，测试用

    ## 方法1：已废弃
    # gate_status_list_new = []    # 闸机开关状态：只保留有人的通道
    # gate_light_status_list_new = []    # 闸机灯状态：只保留有人通道的灯

    # for i in range(len(passway_area_list)):
    #     if i in which_gateList:
    #         gate_status_list_new.append(gate_status_list[i])
    #         gate_light_status_list_new.append(gate_light_status_list[i])

    # 2.2、判断各自通道内的人数

    # # 2.1、先做钻闸机的判定
    # for i in range(len(bboxes)):
    #     box = bboxes[i]    # 当前人
    #     gate_num = which_gateList[i]    # 当前人所在通道
    #     light_status = gate_light_status_list[gate_num]    # 当前通道的指示灯
    #     gate_status = gate_status_list[gate_num]    # 当前通道闸机门的状态
    #     person_cls = classes[i]    # 当前人的类别
    #     person_id = personidArr[i]    # 当前人的id
    #     isCrossed = personIsCrossLine[person_id]    # 当前人是否过线：0没过线；1过线
    #
    #     if gate_status == "closed":    # 当闸机关
    #         if person_cls == "adult":    # 且为大人（小孩站着过都不算逃票，更何况钻过去了）
    #             if light_status == "redLight":    # 且亮红灯
    #                 if isin_throughArea(box) is True:    # 且在钻闸机判定区间内
    #                     if isCrossed == "1":    # 且过线，则认为是钻闸机的逃票
    #                         flag = "WARNING"    # 检测到有逃票，标记位WARNING
    #                         pass_status_list[i] = 4    # 4代表 钻闸机逃票

    # 2.2、尾随逃票情况
    # 2.2.1、分组统计各通道内人数
    gateCounter = Counter(which_gateList)
    print("gateCounter:", gateCounter)
    log.logger.info("各通道内人数 gateCounter: %s" % (gateCounter))    # Counter({1: 1, 2: 1, -1: 1})

    # 2.2.2、找出同一通道出现多人的序列
    multi_personList = []    # 同时出现多人的闸机序列
    for gate_num in gateCounter.keys():
        if gate_num == -1:
            continue    # 通道编号为-1，说明不在有效通道范围内，这些人不做逃票判定
        if gateCounter[gate_num] > 1:
            multi_personList.append(gate_num)    # 拿到几号闸机同时出现多人，后续做尾随逃票判定用

    # 2.2.3、同一通道出现多人的情况
    if len(multi_personList) > 0:    # 否则拿出各通道的人数，计算距离
        passwayPersonDict = {}    # <通道编号，通道内的人员list>
        for i in range(len(which_gateList)):    # 逐个通道获取各通道内的人的序号：
            if which_gateList[i] in multi_personList:
                if which_gateList[i] in passwayPersonDict.keys():
                    tmp = passwayPersonDict.get(which_gateList[i])
                    tmp.append(i)
                    passwayPersonDict[which_gateList[i]] = tmp
                else:
                    passwayPersonDict[which_gateList[i]] = [i]
        print("通道-人对应关系 passwayPersonDict:", passwayPersonDict)    # passwayPersonDict: {2: [0, 1]}，表示2号通道出现了0号人和1号人
        log.logger.info("通道-人对应关系 passwayPersonDict: %s" % (passwayPersonDict))

        for passway in passwayPersonDict.keys():    # 逐个处理每一个通道的多人情况
            personList = passwayPersonDict[passway]    # 拿到该通道内的所有人在bboxes中的序列，passway为通道编号
            default_displacement = gate_default_displacement_list[passway]    # 该通道的画面位移，默认通过该通道是往上还是往下

            suspicion_evade_boxes = [bboxes[person_index] for person_index in personList]  # 同一通道里的所有人框
            suspicion_evade_classes = [classes[person_index] for person_index in personList]    # 同一通道里的所有人类别
            suspicion_evade_personIds = [personidArr[person_index] for person_index in personList]  # 同一通道里的所有人id

            print("通道 %s：人物框：%s，人物类别：%s, 人物ID：%s" % (passway, suspicion_evade_boxes, suspicion_evade_classes, suspicion_evade_personIds))
            log.logger.info("通道 %s：人物框：%s，人物类别：%s, 人物ID：%s" % (passway, suspicion_evade_boxes, suspicion_evade_classes, suspicion_evade_personIds))
            ## 2.3、计算两两之间的距离，通过次距离判断是否属于逃票，center跟suspicion_evade_boxes平级，只是保存坐标点位不同
            center = [[(abs(left) + abs(right)) / 2,
                       (abs(top) + abs(bottom)) / 2] for (left, top, right, bottom) in suspicion_evade_boxes]

            evade_index_list = []       # 涉嫌逃票的序号：在原始bboxes中的序号
            delivery_index_list = []    # 隔闸机递东西的序号：在原始bboxes中的序号
            block_index_list = []       # 阻碍通行：闸机门关，多人在闸机同一侧
            be_tailed_list = []         # 被尾随者：在他身上发生并闸事件

            for i in range(len(center)):    # 每个通道，两两人之间计算距离（i，j表示人在每个通道内的序列）
                for j in range(i + 1, len(center)):
                    person1x, person1y = center[i][0], center[i][1]
                    person2x, person2y = center[j][0], center[j][1]
                    # distance = math.sqrt(((person1x - person2x) ** 2) +
                    #                      ((person1y - person2y) ** 2))
                    centery_distance = abs(person1y - person2y)    # 只算y方向上的，取绝对值

                    print("person1: %s %s, person2: %s %s, distance: %f" % (
                        suspicion_evade_classes[i], center[i], suspicion_evade_classes[j], center[j], centery_distance))
                    log.logger.info("person1: %s %s, person2: %s %s, distance: %f" % (
                        suspicion_evade_classes[i], center[i], suspicion_evade_classes[j], center[j], centery_distance))

                    # 第i个人，第j个人
                    if suspicion_evade_classes[i] in adult_types and suspicion_evade_classes[j] in adult_types:  # 只有当两个人都是大人时

                        person1_forward = personForwardDict[suspicion_evade_personIds[i]]  # 第1个人的方向
                        person2_forward = personForwardDict[suspicion_evade_personIds[j]]  # 第2个人的方向

                        if person1_forward == person2_forward:    # 如果方向相同
                            # 距离不在阀值范围内，continue
                            if centery_distance < down_distance_threshold or centery_distance > up_distance_threshold:
                                continue
                            suspicion1 = suspicion_evade_boxes[center.index(center[i])], suspicion_evade_personIds[
                                center.index(center[i])]  # 嫌疑人1的box，id
                            suspicion2 = suspicion_evade_boxes[center.index(center[j])], suspicion_evade_personIds[
                                center.index(center[j])]  # 嫌疑人2的box，id

                            index1 = bboxes.index(suspicion1[0])  # 涉嫌逃票的两人的全局序号
                            index2 = bboxes.index(suspicion2[0])

                            # 通道 2: adult [1632, 498, 1981, 758] adult [1634, 18, 1876, 158] 涉嫌逃票, distance: 540.000000
                            fmtStr = '''
                                        通道 %s: \n
                                        \t\t 类型: %s 人物: %s \n
                                        \t\t 类型: %s 人物: %s 涉嫌逃票 distance: %f \n
                                        \t\t 这两人真实全局序号: %d %d
                                    ''' % (passway,
                                           suspicion_evade_classes[i], str(suspicion1),
                                           suspicion_evade_classes[j], str(suspicion2), centery_distance,
                                           index1, index2)
                            print(fmtStr)
                            log.logger.info(fmtStr)

                            if default_displacement == "down":  # 向下走的，y轴坐标小的为尾随
                                evade_following_y = min(center[i][1], center[j][1])  # 这里是中心点坐标(x, y)
                            else:
                                evade_following_y = max(center[i][1], center[j][1])

                            evade_following = \
                                [(center[i], i) for i in range(len(center)) if center[i][1] == evade_following_y][0]
                            print("evade_following:", type(evade_following), evade_following, evade_following_y)
                            print("center:", type(center), center)
                            # 尾随的人的box和id
                            suspicion_evade = suspicion_evade_boxes[center.index(evade_following[0])], \
                                              suspicion_evade_personIds[center.index(evade_following[0])]

                            # 被尾随的
                            be_tailed = suspicion2 if suspicion_evade[1] == suspicion1[1] else suspicion1

                            # # 尾随人过线判断：该逻辑不能用。原因：当逃票者过线时，被尾随者已经走出通道，这时通道内仍只有一个人（逃票者）
                            # if personIsCrossLine[suspicion_evade[1]] == "1":    # 尾随人过线，是逃票
                            if gate_light_status_list[passway] == "redLight":  # 此处用红灯预警替代
                                # 这是再加身高的判断因素
                                distance = getNearestDistance(passway, curr_time)  # 此距离为设备到测得物体的距离
                                # person_height = total_height - distance    # 通过的人的身高
                                if distance < gateDistanceDict[
                                    passway] or distance == 0:  # 距离比全程小（说明有物体挡住了），说明是大人（小孩挡不住距离）
                                    print("逃票详情：")
                                    print("逃票者：%s" % str(suspicion_evade))  # (box, id)
                                    print("被尾随：%s" % str(be_tailed))
                                    log.logger.info("逃票详情：")
                                    log.logger.info("逃票者：%s" % str(suspicion_evade))
                                    log.logger.info("被尾随：%s" % str(be_tailed))

                                    following_list.append(suspicion_evade)  # 尾随者id列表
                                    be_tailed_list.append(bboxes.index(be_tailed[0]))  # 被尾随者

                                    pass_distance_list[index1] = centery_distance  # 涉嫌逃票的两人头中心点的距离
                                    pass_distance_list[index2] = centery_distance
                                else:
                                    print("身高不足以购票: %f, 不认为是逃票" % (distance))
                                    log.logger.info("身高不足以购票: %f, 不认为是逃票" % (distance))
                            else:
                                print("尾随者 %s 未过线，不认为逃票" % (str(suspicion_evade)))
            # 判定尾随者是否过线
            print("判断尾随者是否过线。。。")
            log.logger.info("判断尾随者是否过线。。。")
            tmp = []
            for following in following_list:
                print(">>> 当前处理：%s" % (str(following)))
                is_corssed = "0"    # 默认没过线
                try:
                    is_corssed = personIsCrossLine[following[1]]    # 人是否过线："0"未过线，"1"过线
                    is_newed = personForwardDict[following[1]]      # 是否是新人："0"是，"1"不是

                    print("是否过线: %s, 是否新人: %s" % (is_corssed, is_newed))
                    log.logger.info("是否过线: %s, 是否新人: %s" % (is_corssed, is_newed))

                    # if is_newed == "0":
                    #     is_corssed = "1"    # 快过线时id变了的，就当他过线了

                except KeyError as e:
                    # is_corssed = "1"    # 如果没拿到过线信息，说明该人是上一轮遗留的，移除即可
                    tmp.append(following)
                    log.logger.error("该人已被移除: %s, details: %s" % (following, str(traceback.format_exc())))
                    # continue

                if is_corssed == "1":  # 过线
                    flag = "WARNING"  # 检出有人逃票，该标识为WARNING
                    print("检测到涉嫌逃票: %s" % flag)
                    print("尾随者过线: %s" % (str(following)))
                    log.logger.warn("检测到涉嫌逃票: %s" % flag)
                    log.logger.warn("尾随者过线: %s" % (str(following)))

                    try:
                        evade_index_list.append(bboxes.index(following[0]))  # 只有逃票者会被记，被尾随的不会被记录
                    except ValueError as e:    # 有可能存在following是之前遗留的，不是当前轮检测出来的
                        print("先前遗留人（非当前轮检出）: %s" % (str(following)))
                        log.logger.info("先前遗留人（非当前轮检出）: %s" % (str(following)))
                    tmp.append(following)

            # 更新每个人的通行状态
            for i in range(len(evade_index_list)):    # evade_index_list[i]为人在bboxes中的真实序号
                pass_status_list[evade_index_list[i]] = 1    # 更新通过状态为 1涉嫌逃票
            for i in range(len(delivery_index_list)):
                pass_status_list[delivery_index_list[i]] = 2    # 更新通过状态为 2 递东西
            for i in range(len(block_index_list)):
                pass_status_list[block_index_list[i]] = 3    # 更新通行状态为 3 阻碍通行
            for i in range(len(be_tailed_list)):
                pass_status_list[be_tailed_list[i]] = 5      # 更新通行状态为 5并闸事件
            print("更新后的通行状态: %s" % (pass_status_list))
            log.logger.info("更新后的通行状态: %s" % (pass_status_list))

            # 删除following_list中已过线的人
            for t in tmp:
                print("正在删除已过线的人：%s %s" % (type(t), t))
                log.logger.info("正在删除已过线的人：%s %s" % (type(t), t))
                try:
                    following_list.remove(t)
                except ValueError as e:
                    log.logger.error("删除某人失败，info: %s, error: %s" % (str(t), traceback.format_exc()))

    ## 4.更新每个人的track内容：新增：闸机编号、通过状态、闸机门状态、闸机灯状态
    for (track, which_gate, pass_status, pass_distance) in zip(tracks, which_gateList, pass_status_list, pass_distance_list):
        trackContent = TrackContent(gate_num=which_gate,    # 闸机编号
                                    pass_status=pass_status,
                                    pass_distance=pass_distance,
                                    cls=track.classes,    # 人物类别：大人/小孩
                                    score=track.score,
                                    track_id=track.track_id,
                                    state=track.state,
                                    bbox=Box2Line(track.to_tlbr()),
                                    direction=passway_default_direct_list[which_gate],    # 实时视图用默认方向，后续离线全局视图微调
                                    gate_status=gate_status_list[which_gate],    # 闸机门状态：通过闸机编号拿到
                                    gate_light_status=gate_light_status_list[which_gate])    # 闸机灯状态：通过闸机编号拿到
        TrackContentList.append(trackContent)
    return flag, TrackContentList, following_list



'''
    Box转Line：左_上_右_下
'''
def Box2Line(bbox):
    if len(bbox) ==4:
        return "%s_%s_%s_%s" % (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))

'''
    判断人在哪个闸机区域，人以中心点为准
    :param bboxes 所有人的人物框列表，左上右下
    :param passway_area_list 通道范围，从左到右，左上右下
    :return which_gates 通道编号列表，-1表示不在任何框内，仅占位，不做逃票判定
'''
def isin_which_gate(bboxes):
    # print("bboxes:", bboxes)
    # print("passway_area_list:", passway_area_list)
    # iou_result = calc_iou(bbox1=bboxes, bbox2=passway_area_list)
    # which_gates = []
    # for iou in iou_result:
    #     which_gates.append(iou.argmax())    # 找每行iou最大的，认为该人在该通道内
    # return which_gates
    which_gates = []    # 每个人的依次闸机列表，闸机顺序与人物框顺序对应
    for box in bboxes:
        left, top, right, bottom = box
        centerx = (left + right) / 2
        centery = (top + bottom) / 2
        which_gate_num = -1    # 默认通道为-1，认为不在任何通道内

        for i in range(len(passway_area_list)):
            passway_area_left, passway_area_top, passway_area_right, passway_area_bottom = passway_area_list[i]

            # 如果在当前范围内，则认为是在该通道下
            if (centerx >= passway_area_left and centerx <= passway_area_right) and (centery >= passway_area_top and centery <= passway_area_bottom):
                which_gate_num = i    # 该人在第i通道下
                break    # 找到之后就不再循环
        which_gates.append(which_gate_num)
    return which_gates


'''
    匹配检测到的闸机位置与真实位置，拿到真实位置各闸机的开关状态
    :param real_gate_area_list 检测到的闸机位置：左上右下
    :return 返回真实闸机的开关状态序列
'''
def getGateStatusList(real_gate_area_list):
    gate_status_list = ["open"] * len(gate_area_list)    # 默认闸机门都开着，意思是都没检测到
    if real_gate_area_list is None or len(real_gate_area_list) < 1:    # 如果没检测到闸机，说明所有闸机都open
        return gate_status_list
    else:
        # iou_result = calc_iou(bbox1=gate_area_list, bbox2=real_gate_area_list)    # 这样做，当两个闸片分开别识别时，gate_status_list会数组越界
        iou_result = calc_iou(bbox1=real_gate_area_list, bbox2=gate_area_list)    # 行：检测到的闸机区域序列；列：真实位置的闸机区域序列
        print("getGateStatusList.iou_result:", iou_result)
        log.logger.info("getGateStatusList.iou_result: %s" % (iou_result))
        for iou in iou_result:
            print("iou.argmax:", type(iou), iou.argmax(), iou.max())    # 检测np.ndarray中最大值
            log.logger.info("getGateStatusList-iou.argmax: %s %s %s" % (type(iou), iou.argmax(), iou.max()))
            # gate_status_list.append(iou.argmax())
            gate_status_list[iou.argmax()] = "closed"    # 找到跟哪个闸机的iou最大，视为检测到的是谁的
    return gate_status_list

'''
    匹配检测到的灯与真实灯位置
    :param real_gate_light_cls_list 检测到灯的类别序列
    :param real_gate_light_area_list 检测到灯的区域序列
'''
def getGateLightStatusList(real_gate_light_cls_list, real_gate_light_area_list):
    # real_gate_light_cls_list = ['greenLight', 'greenLight']    # 写死，debug用
    # real_gate_light_area_list =  [[1248, 443, 1464, 531], [1815, 422, 1901, 518]]
    gate_light_status_list = []
    for light_area in gate_light_area_list:
        if light_area == [0, 0, 0, 0]:
            gate_light_status_list.append("NoLight")    # 没灯
        else:
            gate_light_status_list.append("whiteLight")    # 默认白灯

    if real_gate_light_area_list is None or len(real_gate_light_area_list) < 1:    # 如果没检测到灯，返回全默认
        return gate_light_status_list
    else:
        iou_result = calc_iou(bbox1=real_gate_light_area_list, bbox2=gate_light_area_list)    # 行：检测到的灯区域序列；列：真实位置灯区域序列
        print("getGateLightStatusList.iou_result:", iou_result)
        log.logger.info("getGateLightStatusList.iou_result: %s" % (iou_result))
        for i in range(len(iou_result)):
            iou = iou_result[i]
            print("getGateLightStatusList-iou.argmax:", type(iou), iou.argmax(), iou.max())    # iou.argmax()，表示最大值所在的下标
            log.logger.info("getGateLightStatusList-iou.argmax: %s %s %s" % (type(iou), iou.argmax(), iou.max()))
            if iou.max() > 0:    # 只有最大iou>0时，才能改状态。避免[0, 0, 0]最大iou是0而修改了第一个灯的状态
                gate_light_status_list[iou.argmax()] = real_gate_light_cls_list[i]    # 第i个值，表示在real_gate_light_area_list的第i行
    return gate_light_status_list


'''
    计算iou
'''
def calc_iou(bbox1, bbox2):
    if not isinstance(bbox1, np.ndarray):
        bbox1 = np.array(bbox1)
    if not isinstance(bbox2, np.ndarray):
        bbox2 = np.array(bbox2)
    xmin1, ymin1, xmax1, ymax1, = np.split(bbox1, 4, axis=-1)
    xmin2, ymin2, xmax2, ymax2, = np.split(bbox2, 4, axis=-1)

    area1 = (xmax1 - xmin1) * (ymax1 - ymin1)
    area2 = (xmax2 - xmin2) * (ymax2 - ymin2)

    ymin = np.maximum(ymin1, np.squeeze(ymin2, axis=-1))
    xmin = np.maximum(xmin1, np.squeeze(xmin2, axis=-1))
    ymax = np.minimum(ymax1, np.squeeze(ymax2, axis=-1))
    xmax = np.minimum(xmax1, np.squeeze(xmax2, axis=-1))

    h = np.maximum(ymax - ymin, 0)
    w = np.maximum(xmax - xmin, 0)
    intersect = h * w

    union = area1 + np.squeeze(area2, axis=-1) - intersect
    return intersect / union

'''
    判断是否属于隔闸机递东西
    :param person1y 第一个人
    :param person2y 第二个人
    :param gate_status 闸机状态
    :param gate_area 闸机门区域
    :return tag，Delivery：递东西；evade：逃票；block：阻碍通行
'''
def isDelivery(person1y, person2y, gate_status, gate_area):
    tag = ""    # 状态
    left, top, right, bottom = gate_area    # 闸机框区域：左上右下
    center_y = int((bottom + top ) / 2)
    if (person1y <= center_y and person2y >= center_y) or (person1y >= center_y and person2y <= center_y):    # 如果两个人在闸机两侧
        if gate_status == "closed":    # 并且闸机门关闭
            tag = "Delivery"    # 递东西
        else:    # 闸机门开，说明涉嫌逃票，不是递东西
            tag = "evade"    # 逃票
    else:    # 两个人在闸机同一侧
        if gate_status == "closed":    # 且闸机门关闭
            tag = "block"    # 阻碍通行
        else:
            tag = "evade"
    return tag

'''
    判定每个人的方向，所在区域，及是否过界
    :param trackList 追踪列表
    :param personBoxDict 每个人的人物框：{person_id: box左上右下}
    :param personForwardDict 每个人的方向状态：{personid: 方向}，0无方向（新人）；1向上；2向下；3丢失（出域）
    :param personLocaDict 每个人的位置：{personid: 位置}，0图像上半截；1图像下半截
    :param personIsCrossLine 每个人是否过线：{personid: 是否过线}，0没过线；1过线
'''
def judgeStatus(trackList, personForwardDict, personBoxDict, personLocaDict, personIsCrossLine):
    curr_person_id_list = []
    for track in trackList:
        person_id = track.track_id  # 人的id
        curr_person_id_list.append(person_id)
        bbox = track.to_tlbr()  # 左上右下
        left, top, right, bottom = bbox
        centery = (top + bottom) / 2

        # 先加新人
        if person_id not in personForwardDict.keys():  # 如果该人第一次来
            personForwardDict[person_id] = "0"  # 新来的
            personBoxDict[person_id] = bbox
            personLocaDict[person_id] = "0" if centery < image_size[1] / 2 else "1"  # 默认在上半图
            personIsCrossLine[person_id] = "0"
        else:
            prev_forward = personForwardDict[person_id]  # 当前人上一帧的方向
            prev_box = personBoxDict[person_id]  # 当前人上一帧的框
            prev_loca = personLocaDict[person_id]  # 当前人上一帧的位置

            prev_left, prev_top, prev_right, prev_bottom = prev_box
            prev_centery = (prev_top + prev_bottom) / 2
            if centery < prev_centery:  # 当前小于上一帧
                personForwardDict[person_id] = "1"  # 方向向上
            else:
                personForwardDict[person_id] = "2"  # 方向向下
            personBoxDict[person_id] = bbox
            currLoca = "0" if centery < image_size[1] / 2 else "1"
            personLocaDict[person_id] = currLoca
            if currLoca == prev_loca:  # 当前位置和上一帧位置比较，相同则没过线，不同则过线
                personIsCrossLine[person_id] = "0"
            else:
                personIsCrossLine[person_id] = "1"
    # 再删旧人
    del_pid_list = []  # 已出界的人
    for pid in personForwardDict.keys():  # 出域的人方向标记为3，
        if pid not in curr_person_id_list:
            personForwardDict[pid] = "3"  # 先标记
            del_pid_list.append(pid)

    # print("curr_person_id_list: %s" % (str(curr_person_id_list)))
    print("正在删除出界的人：%s" % (str(del_pid_list)))
    log.logger.info("正在删除出界的人：%s" % (str(del_pid_list)))
    # 再删除
    for pid in del_pid_list:
        # print("正在删除出界的人：%s %s" % (type(pid), pid))
        del personForwardDict[pid]
        del personBoxDict[pid]
        del personLocaDict[pid]
        del personIsCrossLine[pid]
    return personForwardDict, personBoxDict, personLocaDict, personIsCrossLine

'''
    获取最近时间的距离
    :param gate_num 闸机编号
    :param curr_time 当前时间，字符串类型："%Y%m%d_%H%M%S.%f"
    :return 返回离指定时间最近的距离
'''
def getNearestDistance(gate_num, curr_time):
    start_time = datetime_add(curr_time, s=-1)
    end_time = datetime_add(curr_time, s=1)
    df = getDistanceByTime(gate_num, start_time, end_time)    # 拿到近几秒的距离，df格式
    print("找到距离数据：\n%s" % df)
    log.logger.info("找到距离数据：\n%s" % df)

    if df.empty is True:    # 如果没查到值，直接返回0
        return 0
    else:
        df = df.dropna()
        df['spec_time'] = curr_time
        df['ms_time_stamp'] = pd.to_datetime(df['ms_time'], format="%Y%m%d_%H%M%S.%f")    # 先做成datetime格式的
        df['spec_time_stamp'] = pd.to_datetime(df['spec_time'], format="%Y%m%d_%H%M%S.%f")

        # 再做成long型时间戳进行计算
        df['ms_time_stamp'] = (df['ms_time_stamp'] - np.datetime64('1970-01-01T08:00:00Z')) / np.timedelta64(1, 'ms')
        df['spec_time_stamp'] = (df['spec_time_stamp'] - np.datetime64('1970-01-01T08:00:00Z')) / np.timedelta64(1, 'ms')

        df['ms_interval'] = (df['spec_time_stamp'] - df['ms_time_stamp']).abs()    # 计算时间间距

        # 最后返回最小时间间距所对应的距离值
        result = df[df['ms_interval'] == df['ms_interval'].min()]['distance']
        return result.values[0]

'''
    判断是否在钻闸机的判定区域内
'''
def isin_throughArea(box):
    left, top, right, bottom = box  # 左上右下
    w = right - left
    h = bottom - top
    centerx = left + w / 2
    centery = top + h / 2

    through_left, through_top, through_right, through_bottom = get_through_filter_area()  # 获取钻闸机的判定区域

    if (centerx >= through_left and centerx <= through_right) and (centery >= through_top and centery <= through_bottom):
        return True
    else:
        return False

'''
    获取钻闸机的判定区域
'''
def get_through_filter_area():
    return (int(image_size[0] * through_gate_area[0]), int(image_size[1] * through_gate_area[1]),
            int(image_size[0] * through_gate_area[2]), int(image_size[1] * through_gate_area[3]))