import os
import math
import numpy as np
from collections import Counter
from common.config import up_distance_rate, down_distance_rate, log, adult_types
from common.ContextParam import getContextParam
from common.entity import TrackContent

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

# print("passway_area_list:", passway_area_list)
# print("gate_area_list:", gate_area_list)
# print("gate_light_area_list:", gate_light_area_list)

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
    :return flag, TrackContentList 通行状态，新的追踪人的内容
'''
def evade_vote(tracks, other_classes, other_boxs, other_scores, height):
    TrackContentList = []    # 追踪人的内容，新增闸机编号和通过状态，过滤掉不在有效闸机通道的人员
    flag = "NORMAL"    # 默认该帧图片的通行状态为NORMAL，遇到有逃票时改为WARNING
    up_distance_threshold = height * up_distance_rate
    down_distance_threshold = height * down_distance_rate
    print("人间距上限: %f, 下限: %f" % (up_distance_threshold, down_distance_threshold))
    log.logger.info("人间距上限: %f, 下限: %f" % (up_distance_threshold, down_distance_threshold))

    bboxes = [[int(track.to_tlbr()[0]),
               int(track.to_tlbr()[1]),
               int(track.to_tlbr()[2]),
               int(track.to_tlbr()[3])] for track in tracks]  # 所有人的人物框
    classes = [track.classes for track in tracks]    # 所有人的类别

    print("人物框序列bboxes：%s" % bboxes)
    print("人物类型序列classes：%s" % classes)
    log.logger.info("人物框序列bboxes：%s" % bboxes)
    log.logger.info("人物类型序列classes：%s" % classes)

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

    ## 2.再处理人
    # 2.1、判断各自在哪个通道内
    which_gateList = isin_which_gate(bboxes)    # which_gateList，有人的闸机序列，每个人的框和各自的闸机序列一一对应
    # effective_boxes，有效的人物框，这时已过滤掉了不在有效范围内的框
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
    gateCounter = Counter(which_gateList)
    print("gateCounter:", gateCounter)
    log.logger.info("各通道内人数 gateCounter: %s" % (gateCounter))

    multi_personList = []    # 同时出现多人的闸机序列
    for res in gateCounter.keys():
        if res == -1:
            continue    # 通道编号为-1，说明不在有效通道范围内，这些人不做逃票判定
        if gateCounter[res] > 1:
            multi_personList.append(res)    # 拿到几号闸机同时出现多人

    pass_status_list = [0] * len(bboxes)    # 每个人的通行状态

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
            suspicion_evade_boxes = []  # 同一通道里的所有人框
            suspicion_evade_classes = []    # 同一通道里的所有人类别

            for person_index in personList:    # 逐个分别处理每个通道的情况，而不是所有通道一起处理
                suspicion_evade_boxes.append(bboxes[person_index])
                suspicion_evade_classes.append(classes[person_index])

            print("通道 %s：人物框：%s，人物类别：%s" % (passway, suspicion_evade_boxes, suspicion_evade_classes))
            log.logger.info("通道 %s：人物框：%s，人物类别：%s" % (passway, suspicion_evade_boxes, suspicion_evade_classes))

            ## 2.3、计算两两之间的距离，通过次距离判断是否属于逃票，center跟suspicion_evade_boxes平级，只是保存坐标点位不同
            center = [[abs(left) + (abs(right)- abs(left)) / 2,
                       abs(top) + (abs(bottom) -abs(top)) / 2] for (left, top, right, bottom) in suspicion_evade_boxes]

            evade_index_list = []       # 涉嫌逃票的序号：在原始bboxes中的序号
            delivery_index_list = []    # 隔闸机递东西的序号：在原始bboxes中的序号
            block_index_list = []       # 阻碍通行：闸机门关，多人在闸机同一侧

            for i in range(len(center)):    # 每个通道，两两人之间计算距离
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

                            # 这时还需加入闸机门的判断：如果闸机门关，且两人在闸机门两侧，说明在递东西，pass_status置为2，不属于逃票
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
                                suspicion1 = suspicion_evade_boxes[center.index(center[i])]  # 嫌疑人1
                                suspicion2 = suspicion_evade_boxes[center.index(center[j])]  # 嫌疑人2
                                print("通道 %s: %s %s %s %s 涉嫌逃票, distance: %f" % (
                                    passway, suspicion_evade_classes[i], suspicion1, suspicion_evade_classes[j],
                                    suspicion2, distance))  # [0, 0, 1, 2] [1, 1, 2, 2] 涉嫌逃票
                                log.logger.warn("通道 %s: %s %s %s %s 涉嫌逃票, distance: %f" % (
                                    passway, suspicion_evade_classes[i], suspicion1, suspicion_evade_classes[j],
                                    suspicion2, distance))

                                index1 = bboxes.index(suspicion1)
                                index2 = bboxes.index(suspicion2)
                                print("涉嫌逃票-这两人真实全局序号：", index1, index2)  # 这两人真实序号： 0 2
                                log.logger.warn("涉嫌逃票-这两人真实全局序号: %d %d" % (index1, index2))
                                evade_index_list.append(index1)
                                evade_index_list.append(index2)

                                flag = "WARNING"  # 检出有人逃票，该标识为WARNING
                                log.logger.warn("检测到涉嫌逃票: %s" % flag)

            # 更新每个人的通行状态
            for i in range(len(evade_index_list)):    # evade_index_list[i]为人在bboxes中的真实序号
                pass_status_list[evade_index_list[i]] = 1    # 更新通过状态为 1涉嫌逃票
            for i in range(len(delivery_index_list)):
                pass_status_list[delivery_index_list[i]] = 2    # 更新通过状态为 2 递东西
            for i in range(len(block_index_list)):
                pass_status_list[block_index_list[i]] = 3    # 更新通行状态为 3 阻碍通行
            print("更新后的通行状态: %s" % (pass_status_list))
            log.logger.info("更新后的通行状态: %s" % (pass_status_list))

    ## 3.更新每个人的track内容：新增：闸机编号、通过状态、闸机门状态、闸机灯状态
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
        w = right - left
        h = bottom - top
        centerx = left + w / 2
        centery = top + h / 2
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

