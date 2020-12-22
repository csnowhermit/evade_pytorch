import numpy as np
import torch
from common.evadeUtil import gate_light_area_list, calc_iou, gate_area_list

# print(gate_light_area_list)

# 拿所有闸机灯的序列，与标定的灯序列算iou，
# if iou.max() > 0:    # 只有最大iou>0时，才能改状态。避免[0, 0, 0]最大iou是0而修改了第一个灯的状态
# 此时最大iou设为0.45
# redLight [       1814         428        1904         533] 0.8653907
# greenLight 0.87, (532, 483), (716, 588)

other_classes = ['redLight', 'greenLight']
# other_boxs = [[532, 483, 716, 588], [1814, 428, 1904, 533]]
other_box = [532, 483, 716, 588]
other_scores = [0.8653907, 0.87]


iou_result = calc_iou(bbox1=[other_box], bbox2=gate_light_area_list)    # 行：检测到的灯区域序列；列：真实位置灯区域序列

# print()
# print(iou_result)

# for iou in iou_result:
#     iou.
#     print(iou, iou.argmax(), iou.max())

print(iou_result)
for i in range(len(iou_result)):
    idx = iou_result[i].argmax()    # 表示第idx个
    maxiou = iou_result[i].max()    # 最大的iou
    if maxiou > 0.45:
        print("此灯是真的")

# 原始检出：normalGate [       1554         480        1747         584] 0.8771836
# 原始检出：greenLight [       1268         450        1451         551] 0.8521452
# 原始检出：cloudGate [        165         515         358         594] 0.7912999
# 原始检出：cloudGate [          8         509         153         601] 0.78813416
# 原始检出：normalGate [       1468         488        1542         588] 0.78601265

gate_clses = ['normalGate', 'normalGate']
 # 0.87, (752, 396), (975, 516)
 # 0.86, (993, 394), (1220, 516)
gate_boxs = [[396, 752, 516, 975],
             [394, 993, 516, 1220]]
gate_scores = [0.8771836, 0.8612999, 0.78813416, 0.78601265]


print("gate_area_list:", gate_area_list)
for (other_cls, other_box, other_score) in zip(gate_clses, gate_boxs,
                                                           gate_scores):  # 其他的识别，只标注类别和得分值
    if other_cls in ['cloudGate', 'normalGate']:  # 闸机门用中心点过滤，而不是iou
        top, left, bottom, right = other_box
        centerx = (left + right)/2
        centery = (top+bottom)/2
        # print(centerx, centery)
        print("当前闸机：", centerx, centery)

        for gate_area in gate_area_list:
            gleft, gtop, gright, gbottom = gate_area

            if (centerx >= gleft and centerx <= gright) and (centery >= gtop and centery <= gbottom):
                print(centerx >= gleft, centerx, gleft, gright)
                print(centery >= gtop, centery, gtop, gbottom)
                print("===========")
                print("\t是真的闸机")


