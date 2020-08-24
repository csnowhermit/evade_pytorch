import os

'''
    需要用到的实体类
'''

'''
    摄像头点位-物理位置点位对应关系
'''
class CapLocation:
    def __init__(self, ip, gate_num, direction, default_direct, entrance,
                 entrance_direct, entrance_gate_num, displacement,
                 passway_area, gate_area, gate_light_area):
        self.ip = ip    # 哪个摄像头
        self.gate_num = gate_num    # 画面中闸机编号
        self.direction = direction    # 方向：0出站，1进站，2双向
        self.default_direct = default_direct    # 默认方向：针对2，跟谁在一起就视为谁的方向
        self.entrance = entrance    # 出入口
        self.entrance_direct = entrance_direct    # 出入口的方向：0出站，1进站
        self.entrance_gate_num = entrance_gate_num    # 出入口的第几个闸机，针对一排闸机用多个摄像头的情况
        self.displacement = displacement    # 画面上是向上走（up）还是向下走（down）
        self.passway_area = getBox(passway_area)    # 目标框的格式转换，通道区域
        self.gate_area = getBox(gate_area)    # 闸机门
        self.gate_light_area = getBox(gate_light_area)    # 闸机灯：默认为whiteLight，遇NoLight为无灯（表示画面看不见灯）

'''
    每一个候选框：左上右下
'''
class Box:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

'''
    box格式转换
'''
def getBox(line):
    if line is None or len(line) < 1:
        return None

    arr = line.split("_")
    if len(arr) == 4:
        return Box(int(arr[0]), int(arr[1]), int(arr[2]), int(arr[3]))
    else:
        return None


'''
    追踪人的内容
    原因：tracker.tracks里没有gate_num（闸机编号），pass_status（通过状态），direction（方向）字段，gate_status（闸机门）字段，gate_light_status（闸机灯）字段
'''
class TrackContent:
    def __init__(self, gate_num, pass_status, cls, score, track_id, state, bbox, direction, gate_status, gate_light_status):
        self.gate_num = gate_num    # 闸机编号
        self.pass_status = pass_status    # 通过状态：0正常通过，1涉嫌逃票
        self.cls = cls    # 人物类别
        self.score = score    # 得分值
        self.track_id = track_id    # 人的id
        self.state = state    # 人的状态：1未确认，2已确认，3已丢失
        self.bbox = bbox    # 人物框：左上右下
        self.direction = direction    # 方向：0出站，1进站
        self.gate_status = gate_status    # 闸机门状态：Open、Close（检测到闸机门视为Close）
        self.gate_light_status = gate_light_status    # 闸机灯状态：redLight、greenLight、yellowLight、whiteLight、NoLight

if __name__ == '__main__':
    trackContent = TrackContent(gate_num=0,
                                pass_status=0,
                                cls='child',
                                score=.99,
                                track_id=15,
                                state=1,
                                bbox=[1, 2, 3, 4],
                                direction=0,
                                gate_status='open',
                                gate_light_status='greenLight')

    import json
    # s = eval(trackContent)
    # obj = s.__dict__, ensure_ascii = False
    s = json.dumps(obj=trackContent.__dict__, ensure_ascii=False)
    print(s)






















