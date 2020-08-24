import time
from kazoo.client import KazooClient
from common.config import zkurl, ip

'''
    zk工具：实现注册中心功能
'''

zk = KazooClient(hosts=zkurl)    #如果是本地那就写127.0.0.1
zk.start()    #与zookeeper连接

# 创建临时节点
zk.create('/evade/' + ip, bytes(ip, encoding="utf-8"), ephemeral=True, makepath=True)

# node = zk.get_children('/evade')
print(zk.get_children('/'))
print(zk.get_children('/evade'))
# print(zk.get_children('/evade/' + ip))

while True:
    time.sleep(1)

# zk.stop()    #与zookeeper断开