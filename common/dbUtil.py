import re
import json
import traceback
from common.config import conn, cursor, log, table_name, evade_table_name

'''
    数据库操作工具
'''

'''
    批量入库：识别明细数据
    :param ip 哪个摄像头
    :param curr_time 当前时间：%Y-%m-%d_%H:%M:%S
    :param save_file 图片保存路径
    :param read_time 读取耗时，s
    :param detect_time 检测耗时，s
    :param TrackContentList 被追踪人的明细
    :return 
'''
def saveManyDetails2DB(ip, curr_time, savefile, read_time, detect_time, TrackContentList):
    if table_exists(table_name) is False:
        create_detail_info_table(table_name)
    if table_exists(evade_table_name) is False:
        create_detail_evade_table(evade_table_name)

    for trackContent in TrackContentList:
        try:
            sql = "insert into %s" % (table_name)
            sql = sql + '''
                                             (curr_time, savefile, pass_status, read_time, detect_time, 
                                             predicted_class, score, box, person_id, trackState, 
                                             ip, gate_num, gate_status, gate_light_status, direction) 
                                             VALUES ('%s', '%s', '%s', %f, %f, 
                                                     '%s', %f, '%s', %d, %d, 
                                                     '%s', '%s', '%s', '%s', '%s')
                                        ''' % (curr_time, savefile, trackContent.pass_status, read_time, detect_time,
                                               trackContent.cls, trackContent.score, trackContent.bbox,
                                               trackContent.track_id, trackContent.state,
                                               ip, trackContent.gate_num, trackContent.gate_status,
                                               trackContent.gate_light_status, trackContent.direction)
            cursor.execute(sql)
            conn.commit()
            sql = ""
            log.logger.info("persist to table: %s" % (table_name))

            if trackContent.pass_status == 1:    # 涉嫌逃票的，再单独保存下
                sql = "insert into %s" % (evade_table_name)
                sql = sql + '''
                                (curr_time, savefile, pass_status, read_time, detect_time, 
                                predicted_class, score, box, person_id, trackState, 
                                ip, gate_num, gate_status, gate_light_status, direction) 
                                VALUES ('%s', '%s', '%s', %f, %f, 
                                        '%s', %f, '%s', %d, %d, 
                                        '%s', '%s', '%s', '%s', '%s')
                            ''' % (curr_time, savefile, trackContent.pass_status, read_time, detect_time,
                                   trackContent.cls, trackContent.score, trackContent.bbox, trackContent.track_id,trackContent.state,
                                   ip, trackContent.gate_num, trackContent.gate_status, trackContent.gate_light_status, trackContent.direction)
                cursor.execute(sql)
                conn.commit()
                sql = ""
                log.logger.info("persist to table: %s" % (evade_table_name))
        except Exception as e:
            log.logger.error(traceback.format_exc())
            log.logger.error("\n%s" % sql)
            conn.rollback()
    return 0

'''
    判断表是否存在
    :param table_name 表名
    :return True，表存在；False，表不存在
'''
def table_exists(table_name):
    sql = "show tables;"
    cursor.execute(sql)
    tables = [cursor.fetchall()]
    table_list = re.findall('(\'.*?\')',str(tables))
    table_list = [re.sub("'",'',each) for each in table_list]
    if table_name in table_list:
        return True
    else:
        return False

'''
    创建信息明细表
    :return ret 0，创建成功
'''
def create_detail_info_table(table_name):
    sql = '''
        CREATE TABLE `%s`  (
            `curr_time` varchar(50) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '当前时刻，精确到s',
            `savefile` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '保存文件路径',
            `pass_status` varchar(2) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '通过状态：0正常通过，1涉嫌逃票',
            `read_time` float(10, 5) NULL DEFAULT NULL COMMENT '读取耗时',
            `detect_time` float(10, 5) NULL DEFAULT NULL COMMENT '检测耗时',
            `predicted_class` varchar(50) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '检测类别',
            `score` float(10, 5) NULL DEFAULT NULL COMMENT '得分值',
            `box` varchar(50) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '人头框，左上右下',
            `person_id` int(10) NULL DEFAULT NULL COMMENT '人物id',
            `trackState` int(2) NULL DEFAULT NULL COMMENT '确认状态：1未确认，2已确认',
            `ip` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '摄像机ip',
            `gate_num` varchar(2) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '闸机编号',
            `gate_status` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '闸机门状态',
            `gate_light_status` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '闸机灯状态',
            `direction` varchar(2) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '方向：0出站，1进站'
        ) ENGINE = InnoDB CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;
    ''' % (table_name)

    ret = cursor.execute(sql)
    log.logger.info("%s 表已创建: %s" % (table_name, ret))
    return ret

'''
    创建逃票信息明细表
    :return ret 0，创建成功
'''
def create_detail_evade_table(evade_table_name):
    sql = '''
        CREATE TABLE `%s`  (
            `uuid` int(50) NOT NULL AUTO_INCREMENT COMMENT '自增id',
            `curr_time` varchar(50) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '当前时刻，精确到s',
            `savefile` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '保存文件路径',
            `pass_status` varchar(2) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '通过状态：0正常通过，1涉嫌逃票',
            `read_time` float(10, 5) NULL DEFAULT NULL COMMENT '读取耗时',
            `detect_time` float(10, 5) NULL DEFAULT NULL COMMENT '检测耗时',
            `predicted_class` varchar(50) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '检测类别',
            `score` float(10, 5) NULL DEFAULT NULL COMMENT '得分值',
            `box` varchar(50) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '人头框，左上右下',
            `person_id` int(10) NULL DEFAULT NULL COMMENT '人物id',
            `trackState` int(2) NULL DEFAULT NULL COMMENT '确认状态：1未确认，2已确认',
            `ip` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '摄像机ip',
            `gate_num` varchar(2) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '闸机编号',
            `gate_status` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '闸机门状态',
            `gate_light_status` varchar(255) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '闸机灯状态',
            `direction` varchar(2) CHARACTER SET utf8mb4 NULL DEFAULT NULL COMMENT '方向：0出站，1进站', 
            PRIMARY KEY (`uuid`) USING BTREE
        ) ENGINE = InnoDB CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;
    ''' % (evade_table_name)

    ret = cursor.execute(sql)
    log.logger.info("%s 表已创建: %s" % (evade_table_name, ret))
    return ret

'''
    获取当前最大person_id
'''
def getMaxPersonID():
    if table_exists(table_name) is False:
        create_detail_info_table(table_name)

    sql = "select max(person_id) from %s;" % (table_name)    # 找正常表中最大值
    cursor.execute(sql)
    results = cursor.fetchall()    # results[0], <class 'tuple'>
    if results[0][0] is None:
        max_person_id = 0
    else:
        max_person_id = results[0][0]

    log.logger.info("start person_id：%d" % max_person_id)
    return max_person_id

if __name__ == '__main__':
    # print(table_exists("details_10.6.8.181"))
    # print(table_exists("details_10.6.8.222"))
    #
    # if table_exists(table_name) is False:
    #     print(create_detail_info_table(table_name))
    # else:
    #     print(table_name + " 表已存在")
    print(getMaxPersonID())