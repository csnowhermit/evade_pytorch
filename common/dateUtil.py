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

'''
    获取指定n天前的日期
    :param n n为负数则为指定n天后的日期
'''
def getAppointDate(n=1):
    today = datetime.date.today()
    nday = datetime.timedelta(days=n)
    nbefore = today - nday
    return nbefore.strftime("%Y%m%d")

'''
    获取前n秒/后n秒的时间
    :param 时间，字符串格式的
    :param 时间，格式化字符串，默认到毫秒级
    :param s 往前到多少秒，默认往后1s
    :return 返回调整后的时间，按fmtStr格式化后返回
'''
def datetime_add(timeStr, fmtStr="%Y%m%d_%H%M%S.%f", s=1):
    dd = datetime.datetime.strptime(timeStr, fmtStr)
    dd = dd + datetime.timedelta(seconds=s)
    return dd.strftime(fmtStr)


if __name__ == '__main__':
    print(formatTimestamp(time.time()))
    print(formatTimestamp(time.time(), format="%Y-%m-%d_%H:%M"))
    print(formatTimestamp(time.time(), format="%Y-%m-%d_%H:%M:%S", ms=True))
    print(type(getAppointDate()), getAppointDate())

    timeStr = "20201208_095042"
    print(timeStr)
    print(datetime_add(timeStr))
    print(datetime_add(timeStr, s=20))
    print(datetime_add(timeStr, s=-10))

    dd1 = datetime.datetime.strptime("20201208_095734.069", "%Y%m%d_%H%M%S.%f")
    dd2 = datetime.datetime.strptime("20201208_095733.930", "%Y%m%d_%H%M%S.%f")
    r = dd1 - dd2
    print(type(r), r)
    print(r.microseconds)    # 微秒
