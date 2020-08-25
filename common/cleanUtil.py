import os
from common.config import person_types, goods_types, log, image_size, effective_area_rate, person_types_threahold
from common.person_nms import calc_special_nms

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
            if is_effective(xyxy) is True:  # 只有在有效范围内，才算数
                if score >= person_types_threahold:  # 只有大于置信度的，才能视为人头
                    special_classes.append(predicted_class)
                    left, top, right, bottom = xyxy
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
    根据config.py的image_size，effective_area_rate，计算有效区域
    :return 返回有效区域：左上右下
'''
def get_effective_area():
    center = (image_size[0]/2, image_size[1]/2)    # 中心点坐标
    width = image_size[0] * effective_area_rate[0]    # 有效区域宽度
    height = image_size[1] * effective_area_rate[1]    # 有效区域高度

    return (int(center[0] - width / 2), int(center[1] - height / 2), int(center[0] + width / 2), int(center[1] + height / 2))


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