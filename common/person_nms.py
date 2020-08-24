from common.evadeUtil import calc_iou
from common.config import person_nms_iou, child_types, adult_types

'''
    小孩识别成大人，物品识别成小孩 等重叠识别问题，做nms
'''

'''
    手动做一次nms，处理 小孩识别成大人，背包识别成人 等情况
    :param special_classes 人的类别
    :param special_boxs 左上右下
    :param special_scores 得分值
'''
def calc_special_nms(special_classes, special_boxs, special_scores):
    # 对人物单独做一次nms
    nms_box_indexes = []    # 被抑制掉的框序号
    for i in range(len(special_boxs)):
        for j in range(i + 1, len(special_boxs)):  # i+1起步，避免跟自身算iou
            box1 = special_boxs[i]
            box2 = special_boxs[j]

            # if person_classes[i] == person_classes[j]:  # 同类不用算这个
            #     continue
            iou_result = calc_iou(box1, box2)
            # if iou_result == 1:
            # print(i, j, iou_result[0])
            if iou_result[0] > 0.0 and iou_result[0] <= 1.0:  # 如果两个不同框有交集，<=1.0，出现过两个不同人完全相同框的情况
                if iou_result[0] > person_nms_iou:        # 且大于阀值
                    # final = max(person_scores[i], person_scores[j])    # 谁得分大就选定是谁
                    if special_scores[i] > special_scores[j]:
                        final = j
                    else:
                        final = i
                    nms_box_indexes.append(final)
                    # print("now:", nms_box_indexes)
            else:
                pass

    adult_classes = []
    adult_scores = []
    adult_boxs = []    # 大人，左上右下

    child_classes = []
    child_scores = []
    child_boxs = []    # 小孩，左上右下

    goods_classes = []
    goods_scores = []
    goods_boxs = []    # 随身物品，上左下右（要跟闸机等相同）

    for i in range(len(special_classes)):
        if i not in nms_box_indexes:
            if special_classes[i] in child_types:
                child_classes.append(special_classes[i])
                box = special_boxs[i]
                left, top, right, bottom = box
                child_boxs.append([int(left), int(top), int(right - left), int(bottom - top)])      # 转为 左上宽高，供tracker用

                child_scores.append(special_scores[i])
            elif special_classes[i] in adult_types:
                adult_classes.append(special_classes[i])
                box = special_boxs[i]
                left, top, right, bottom = box
                adult_boxs.append([int(left), int(top), int(right - left), int(bottom - top)])  # 转为 左上宽高，供tracker用

                adult_scores.append(special_scores[i])
            else:    # 物品类
                goods_classes.append(special_classes[i])
                box = special_boxs[i]
                left, top, right, bottom = box
                goods_boxs.append([int(top), int(left), int(bottom), int(right)])    # 转为 上左下右，和闸机等一致

                goods_scores.append(special_scores[i])
    return (adult_classes, adult_boxs, adult_scores), (child_classes, child_boxs, child_scores), (goods_classes, goods_boxs, goods_scores)

if __name__ == '__main__':
    person_classes = ['child', 'head', 'head']
    person_scores = [0.4166157, 0.61927605, 0.9575744]
    person_boxs = [[542.0016, 278.24387, 600.6658, 355.25095], [537.6127, 283.58765, 604.105, 350.898], [546.5691, 78.46593, 627.095, 171.85654]]

    person_classes, person_boxs, person_scores = calc_special_nms(person_classes, person_boxs, person_scores)

    print(person_classes)
    print(person_boxs)
    print(person_scores)