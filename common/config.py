import os
import pymysql
import hashlib
from common.Logger import Logger as Logger

'''
    本实例的配置项
'''

# 注册中心
zkurl = "127.0.0.1:2181"

# 连接摄像头
ip = "10.6.8.181"
rtsp_url = "rtsp://admin:quickhigh123456@192.168.120.155/h264/ch1/sub/av_stream"    # 用子码流读取

# appid
# thispath = os.path.abspath(__file__)
# appid = hashlib.md5(thispath.encode("utf-8")).hexdigest()[-8:]    # appid计算方法
# print(appid)
appid = "c90d7f6e"


# 图像大小
image_shape = "1920x1080"
image_size = (1920, 1080)    # 图片大小

# # 图像有效区域比例，以中心点算
# effective_area_rate = (1, 0.9)    # 宽，高。表示宽维度上所有都有效，高维度上由中心点算起，最中间的90%区域有效（即上下各有5%的留白区）
effective_area_rate = (0, 0.17, 1, 0.78)    # 真实有效区域：(1920*0, 1080*0.17, 1920*1, 1080*0.78)

# 各个通道小孩过滤修正线
child_correct_line2 = (0.76, 0.92)    # 表示2号闸机的小孩修正线（人头最右侧位于该区域内的，认为是小孩）


# 数据库
conn = pymysql.connect(host='127.0.0.1',
                       port=3306,
                       user='root',
                       password='123456',
                       database='evade',
                       charset='utf8mb4')
cursor = conn.cursor()

table_name = "details_%s" % (ip.replace(".", "_"))    # 表名：正常+逃票
evade_table_name = "evade_details"    # 逃票表（所有摄像头都存一张表）

# 需特殊处理的类别
person_types = ['adult', 'person', 'child']
# tracker_type = 'adult'    # 需要tracker的类别
adult_types = ['adult', 'person']    # 大人的表现类别
child_types = ['child']    # 小孩的表现类别
goods_types = ['backpack', 'cell phone', 'umbrella', 'handbag', 'pushcart', 'trunk']    # 其他的表现类别

# 人头的置信度下限
person_types_threahold=0.62    # 只有大于等于该置信度的才能认为是人头

# 保存路径（按ip+appid区分）
normal_save_path = "D:/monitor_images/" + ip + appid + "/normal_images/"
evade_save_path = "D:/monitor_images/" + ip  + appid + "/evade_images/"
evade_origin_save_path= "D:/monitor_images/" + ip + appid + "/evade_origin_images/"    # 保存检出逃票的原图
evade_video_path = "D:/monitor_images/" + ip + appid + "/evade_video/"    # 逃票图片的前后视频

if os.path.exists(normal_save_path) is False:
    os.makedirs(normal_save_path)
if os.path.exists(evade_save_path) is False:
    os.makedirs(evade_save_path)
if os.path.exists(evade_origin_save_path) is False:
    os.makedirs(evade_origin_save_path)
if os.path.exists(evade_video_path) is False:
    os.makedirs(evade_video_path)

# 视频原图数据帧list大小
imgCacheSize = 30 * 60 * 1    # 默认存2分钟的图片
imgNearSize = 30 * 5    # 用前后n秒的图片合成视频

# 通过状态的判断条件：图像的高*比例，在两比例之间，认定为涉嫌逃票
up_distance_rate = 0.6
down_distance_rate = 0.2

# 日志文件
logfile = 'D:/evade_logs/evade_%s_%s.log' % (ip, appid)
print(logfile)
# logfile = 'D:/evade_logs/evade.log'    # 多路摄像机同时接入一个实例识别时，用这个log
log = Logger(logfile, level='info')


# 检出框与tracker框的iou，解决人走了框还在的情况
track_iou = 0.45

# 小孩识别成大人，做nms的iou阀值
person_nms_iou = 0.6

# 除逃票外的通行状态类型
pass_status_type_list = ['Delivery', 'block']

# FTP日志
ftp_ip = "192.168.0.27"
ftp_username = "vdog"
ftp_password = "123456"
ftp_log = 'D:/evade_logs/ftp_%s.log' % ip

table_ftpLog = "ftplog_%s" % (ip.replace(".", "_"))    # ftp日志表
