import time
import datetime

# print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

'''
    格式化时间戳
    :param timestamp time.time()
    :param format 指定格式
    :param ms 是否需要精确到毫秒，默认不需要
'''
def formatTimestamp(timestamp, format="%Y-%m-%d_%H:%M:%S", ms=False):
    time_tuple = time.localtime(timestamp)
    data_head = time.strftime(format, time_tuple)
    if ms is False:
        return data_head
    else:
        data_secs = (timestamp - int(timestamp)) * 1000
        data_ms = "%s.%03d" % (data_head, data_secs)
        return data_ms


if __name__ == '__main__':
    print(formatTimestamp(time.time()))
    print(formatTimestamp(time.time(), format="%Y-%m-%d_%H:%M"))
    print(formatTimestamp(time.time(), format="%Y-%m-%d_%H:%M:%S", ms=True))