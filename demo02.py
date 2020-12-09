import time
import datetime
from common.dateUtil import formatTimestamp

# 范围时间
start_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '05:30', '%Y-%m-%d%H:%M')
end_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '23:42', '%Y-%m-%d%H:%M')

print(start_time)
print(end_time)

# # 当前时间
# n_time = datetime.datetime.now()
# # n_time = formatTimestamp(1607528477)
#
# ltime=time.localtime(1395025933)
# timeStr=time.strftime("%Y-%m-%d %H:%M", ltime)
# print(type(timeStr), timeStr)

read_time = 1607528477.123456
n_time = datetime.datetime.fromtimestamp(read_time)
print(type(n_time), n_time)

# 判断当前时间是否在范围时间内
if n_time >= start_time and n_time <= end_time:
    print("running")
else:
    print("sleep")