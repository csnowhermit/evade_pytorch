from common.evadeUtil import calc_iou
from common.config import track_iou, log

'''
    track工具类：根据当前人物框，从track中拿到有用的框
'''

def getUsefulTrack(person_boxs, tracks, person_type):
    trackList = []
    if len(person_boxs) > 0 and len(tracks) > 0:  # 确保追踪器有值，避免calc_iou出错
        person_boxs_ltbr = [[person[0],
                             person[1],
                             person[0] + person[2],
                             person[1] + person[3]] for person in person_boxs]  # 大人：左上宽高-->左上右下

        tmp_tracks = [track for track in tracks if track.classes == person_type]    # 找出要过滤的一类人

        track_box = [[int(track.to_tlbr()[0]),
                      int(track.to_tlbr()[1]),
                      int(track.to_tlbr()[2]),
                      int(track.to_tlbr()[3])] for track in tracks]  # 追踪器中的人

        if len(person_boxs_ltbr) > 0 and len(track_box) > 0:
            iou_result = calc_iou(bbox1=person_boxs_ltbr, bbox2=track_box)  # 计算iou，做无效track框的过滤
            which_track = []
            for iou in iou_result:
                if iou.max() > track_iou:  # 如果最大iou>0.45，则认为是这个人
                    which_track.append(iou.argmax())  # 保存tracker.tracks中该人的下标（这里是track_iou的下标，而不是tracks的下标）
            # 在tracker.tracks中移除不在which_track的元素
            # for i in range(len(tracks)):
            #     if i in which_track:
            #         trackList.append(tracks[i])
            for i in which_track:  # 以上3行逻辑等价于这个，i在which_track中表示tracks中第i个人
                trackList.append(tracks[i])
                print("追踪器中有效的人：%s %s" % (tracks[i].to_tlbr(), tracks[i].classes))
                log.logger.info("追踪器中有效的人：%s %s" % (tracks[i].to_tlbr(), tracks[i].classes))
    return trackList

