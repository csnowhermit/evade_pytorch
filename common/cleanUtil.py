import os
from common.config import person_types, goods_types, log, image_size, effective_area_rate, person_types_threahold, child_correct_line2, head_filter_area_rate, head_filter_woh0, head_filter_area0, head_filter_area1, head_filter_area2
from common.person_nms import calc_special_nms
from common.evadeUtil import isin_which_gate

'''
    对原始检出框及类型进行清洗
    :param bbox_xyxy 原始检出框：左上右下
    :param cls_conf 每个框的置信度
    :param cls_ids 每个框的类别序号
    :param class_names 所有类别集合：通过类别序号从集合中拿到类别名称
    :return 大人、小孩、物品分别的类别、框、置信度，其中，大人和小孩为：左上宽高；物品为：上左下右
'''
def cleaning_box(bbox_xyxy, cls_conf, cls_ids, class_names):
    special_classes = []  # 人，物品
    special_boxs = []
    special_scores = []

    other_classes = []  # 其他物品，只用来显示
    other_boxs = []
    other_scores = []

    # 1.按需做框格式的转换
    for (xyxy, score, id) in zip(bbox_xyxy, cls_conf, cls_ids):
        predicted_class = class_names[id]    # 类别
        print("原始检出：%s %s %s" % (predicted_class, xyxy, score))
        log.logger.info("原始检出：%s %s %s" % (predicted_class, xyxy, score))

        if predicted_class in person_types:  # 如果是人，只有在有效区域内才算
            # 这里做有效区域范围的过滤，解决快出框了person_id变了的bug
            # if True:
            if is_effective(xyxy) is True:  # 只有在有效范围内，才算数
                if score >= person_types_threahold:  # 只有大于置信度的，才能视为人头
                    left, top, right, bottom = xyxy
                    pred_cls = fix_person_type(xyxy, predicted_class)    # 修正人物类型
                    special_classes.append(pred_cls)
                    special_boxs.append([left, top, right, bottom])  # 左上右下，经过calc_special_nms()才转为 左上宽高
                    special_scores.append(score)
        elif predicted_class in goods_types:  # 随身物品，直接算
            special_classes.append(predicted_class)
            left, top, right, bottom = xyxy
            special_boxs.append([left, top, right, bottom])  # 左上右下，经过calc_special_nms()才转为 左上宽高
            special_scores.append(score)
        else:  # 其他类别的格式：上左下右
            other_classes.append(predicted_class)
            left, top, right, bottom = xyxy
            other_boxs.append([top, left, bottom, right])
            other_scores.append(score)

    # 2.单独对人和物做nms，确保每个人/物只有一个框
    (adult_classes, adult_boxs, adult_scores), \
    (child_classes, child_boxs, child_scores), \
    (goods_classes, goods_boxs, goods_scores) = calc_special_nms(special_classes, special_boxs, special_scores)

    other_classes = other_classes + goods_classes
    other_boxs = other_boxs + goods_boxs
    other_scores = other_scores + goods_scores
    return (adult_classes, adult_boxs, adult_scores), (child_classes, child_boxs, child_scores), (other_classes, other_boxs, other_scores)


'''
    根据所处位置和面积比率修正人物类型：大人/小孩
    :param xyxy 人物框：左上右下
    :param predicted_class 预测到的框
    :return 返回修正后的人物类型
'''
def fix_person_type(xyxy, predicted_class):
    # left, top, right, bottom = xyxy
    # pred_cls = ""
    #
    # # 1.对1号通道做小孩/大人的人物框面积做过滤
    # if isin_headFilterArea(xyxy) is True:  # 如果在人头面积过滤区域
    #     head_area = (right - left) * (bottom - top)
    #     head_ratio = float(head_area / (image_size[0] * image_size[1]))
    #     if head_ratio < head_area_filter_ratio:  # 人头面积小于阀值，认为是小孩
    #         pred_cls = "child"
    #     else:  # 否则，该是啥就是啥
    #         pred_cls = predicted_class
    # elif right >= passway_area2[0] and right <= passway_area2[1]:    # 对2号通道做小孩认定区域的过滤：人头最右侧在2号通道的小孩认定区域内
    #     pred_cls = "child"
    # else:
    #     pred_cls = predicted_class  # 否则，该是啥就是啥

    def fix_gate0(xyxy, predicted_class):
        left, top, right, bottom = xyxy
        pred_cls = predicted_class

        if isin_headFilterArea(xyxy, 0) is True:    # 在0号闸机的人头修正区域
            pwidth_ratio = (right - left) / image_size[0]
            pheight_ratio = (bottom - top) / image_size[1]
            width_over_height = pwidth_ratio / pheight_ratio    # 宽高比
            area_ratio = pwidth_ratio * pheight_ratio
            if width_over_height >= head_filter_woh0[0] and width_over_height <= head_filter_woh0[1]:
                if area_ratio >= head_filter_area0[0] and area_ratio <= head_filter_area0[1]:
                    pred_cls = "child"    # 只有当宽高比和面积均满足条件时，才被修正为child
        return pred_cls

    def fix_gate1(xyxy, predicted_class):
        left, top, right, bottom = xyxy
        pred_cls = predicted_class

        if isin_headFilterArea(xyxy, 1) is True:
            head_area = (right - left) * (bottom - top)
            head_ratio = float(head_area / (image_size[0] * image_size[1]))
            if head_ratio >= head_filter_area1[0] and head_ratio <= head_filter_area1[1]:  # 人头面积小于阀值，认为是小孩
                pred_cls = "child"
        return pred_cls

    def fix_gate2(xyxy, predicted_class):
        left, top, right, bottom = xyxy
        pred_cls = predicted_class
        passway_area2 = (
        image_size[0] * child_correct_line2[0], image_size[0] * child_correct_line2[1])  # 2号通道小孩的认定范围（按人物框最右侧算）

        if isin_headFilterArea(xyxy, 2) is True:
            head_area = (right - left) * (bottom - top)
            head_ratio = float(head_area / (image_size[0] * image_size[1]))
            if head_ratio >= head_filter_area2[0] and head_ratio <= head_filter_area2[1]:  # 人头面积
                pred_cls = "child"

            if right >= passway_area2[0] and right <= passway_area2[1]:    # 人头右边框线
                pred_cls = "child"
        return pred_cls

    fix_dict = {0: fix_gate0,
                1: fix_gate1,
                2: fix_gate2}

    # 先判断人在哪个闸机下：
    tmpList = []
    tmpList.append(xyxy)
    which_gate = isin_which_gate(tmpList)[0]
    pred_cls = predicted_class
    if which_gate != -1:    # 对真正在通道内的做修正
        method = fix_dict.get(which_gate)
        if method:
            pred_cls = method(xyxy, predicted_class)
    return pred_cls


'''
    根据config.py的image_size，effective_area_rate，计算有效区域
    :return 返回有效区域：左上右下
'''
def get_effective_area():
    center = (image_size[0]/2, image_size[1]/2)    # 中心点坐标
    width = image_size[0] * effective_area_rate[0]    # 有效区域宽度
    height = image_size[1] * effective_area_rate[1]    # 有效区域高度

    return (int(center[0] - width / 2), int(center[1] - height / 2), int(center[0] + width / 2), int(center[1] + height / 2))


'''
    小孩人头框面积过滤区域
'''
def get_head_filter_area(gate_num):
    # 只算指定区域的
    head_filter_area = head_filter_area_rate[gate_num]
    # (1920*0.36, 1080*0.17, 1920*0.7, 1080*0.78)
    return (int(image_size[0] * head_filter_area[0]), int(image_size[1] * head_filter_area[1]),
            int(image_size[0] * head_filter_area[2]), int(image_size[1] * head_filter_area[3]))

'''
    判断人物框是否在面积过滤区间内
    :param box 原始检出的box，左上右下
    :return True，在有效区间内；False，不在有效区间内
'''
def isin_headFilterArea(box, gate_num):
    left, top, right, bottom = box    # 左上右下
    w = right - left
    h = bottom - top
    centerx = left + w / 2
    centery = top + h / 2

    filter_left, filter_top, filter_right, filter_bottom = get_head_filter_area(gate_num)    # 标定的有效区域为：左上右下

    if (centerx >= filter_left and centerx <= filter_right) and (centery >= filter_top and centery <= filter_bottom):
        return True
    else:
        return False

'''
    判断人物框是否在有效区间内
    :param box 原始检出的box，左上右下
    :return True，在有效区间内；False，不在有效区间内
'''
def is_effective(box):
    left, top, right, bottom = box    # 左上右下
    w = right - left
    h = bottom - top
    centerx = left + w / 2
    centery = top + h / 2

    effective_left, effective_top, effective_right, effective_bottom = get_effective_area()    # 标定的有效区域为：左上右下

    if (centerx >= effective_left and centerx <= effective_right) and (centery >= effective_top and centery <= effective_bottom):
        return True
    else:
        return False