#!/usr/bin/python
# -*- coding: UTF-8 -*-

from ftplib import FTP
import os
import sys
import time
import socket
from common.config import ftp_log

'''
    FTP操作类
'''
class MyFTP:
    def __init__(self, host, port=21):
        self.host = host
        self.port = port
        self.ftp = FTP()
        # 重新设置下编码方式
        self.ftp.encoding = 'gbk'
        self.log_file = open(ftp_log, "a")
        self.file_list = []

    def login(self, username, password):
        try:
            timeout = 60
            socket.setdefaulttimeout(timeout)
            # 0主动模式 1 #被动模式
            self.ftp.set_pasv(False)
            # 打开调试级别2，显示详细信息
            # self.ftp.set_debuglevel(2)

            self.debug_print('开始尝试连接到 %s' % self.host)
            self.ftp.connect(self.host, self.port)
            self.debug_print('成功连接到 %s' % self.host)

            self.debug_print('开始尝试登录到 %s' % self.host)
            self.ftp.login(username, password)
            self.debug_print('成功登录到 %s' % self.host)

            self.debug_print(self.ftp.welcome)
        except Exception as err:
            self.deal_error("FTP 连接或登录失败 ，错误描述为：%s" % err)
            pass

    # 判断远程文件和本地文件大小是否一致
    def is_same_size(self, local_file, remote_file):
        try:
            remote_file_size = self.ftp.size(remote_file)
        except Exception as err:
            # self.debug_print("is_same_size() 错误描述为：%s" % err)
            remote_file_size = -1

        try:
            local_file_size = os.path.getsize(local_file)
        except Exception as err:
            # self.debug_print("is_same_size() 错误描述为：%s" % err)
            local_file_size = -1

        self.debug_print('local_file_size:%d  , remote_file_size:%d' % (local_file_size, remote_file_size))
        if remote_file_size == local_file_size:
            return 1
        else:
            return 0

    # 从ftp下载单个文件
    def download_file(self, local_file, remote_file):
        self.debug_print("download_file()---> local_path = %s ,remote_path = %s" % (local_file, remote_file))

        if self.is_same_size(local_file, remote_file):
            self.debug_print('%s 文件大小相同，无需下载' % local_file)
            return
        else:
            try:
                self.debug_print('>>>>>>>>>>>>下载文件 %s ... ...' % local_file)
                buf_size = 1024
                file_handler = open(local_file, 'wb')
                self.ftp.retrbinary('RETR %s' % remote_file, file_handler.write, buf_size)
                file_handler.close()
            except Exception as err:
                self.debug_print('下载文件出错，出现异常：%s ' % err)
                return

    # 从远程目录下载多个文件到本地目录
    def download_file_tree(self, local_path, remote_path):
        print("download_file_tree()---> local_path = %s, remote_path = %s" % (local_path, remote_path))
        try:
            self.ftp.cwd(remote_path)
        except Exception as err:
            self.debug_print('远程目录%s不存在，继续...' % remote_path + " ,具体错误描述为：%s" % err)
            return

        if not os.path.isdir(local_path):
            self.debug_print('本地目录%s不存在，先创建本地目录' % local_path)
            os.makedirs(local_path)

        self.debug_print('切换至目录: %s' % self.ftp.pwd())

        self.file_list = []
        # 方法回调
        self.ftp.dir(self.get_file_list)

        remote_names = self.file_list
        self.debug_print('远程目录 列表: %s' % remote_names)
        for item in remote_names:
            file_type = item[0]
            file_name = item[1]
            local = os.path.join(local_path, file_name)
            if file_type == 'd':
                print("download_file_tree()---> 下载目录： %s" % file_name)
                self.download_file_tree(local, file_name)
            elif file_type == '-':
                print("download_file()---> 下载文件： %s" % file_name)
                self.download_file(local, file_name)
            self.ftp.cwd("..")
            self.debug_print('返回上层目录 %s' % self.ftp.pwd())
        return True

    # 上传本地文件到ftp
    def upload_file(self, local_file, remote_file):
        if not os.path.isfile(local_file):
            self.debug_print('%s 不存在' % local_file)
            return

        if self.is_same_size(local_file, remote_file):
            self.debug_print('跳过相等的文件: %s' % local_file)
            return

        buf_size = 1024
        file_handler = open(local_file, 'rb')
        self.ftp.storbinary('STOR %s' % remote_file, file_handler, buf_size)
        file_handler.close()
        self.debug_print('上传: %s' % local_file + "成功!")

    '''
        创建ftp远程目录
    '''
    def create_ftp_path(self, remote_path):
        try:
            self.ftp.cwd(remote_path)  # 切换工作路径，抛异常，说明该路径不存在
        except Exception as e:
            # base_dir, part_path = self.ftp.pwd(), remote_path.split('/')    # 这里base_dir不能用当前路径，应该每次从根目录开始
            base_dir, part_path = "/", remote_path.split('/')
            for p in part_path[1:-1]:
                base_dir = base_dir + p + '/'  # 拼接子目录
                try:
                    self.ftp.cwd(base_dir)  # 切换到子目录, 不存在则异常
                except Exception as e:
                    print('INFO:', e)
                    self.ftp.mkd(base_dir)  # 不存在创建当前子目录
                    print("INFO: 已创建目录: %s" % (base_dir))
                    self.debug_print("INFO: 已创建目录: %s" % (base_dir))

    # 上传本地目录到服务器
    def upload_file_tree(self, local_path, remote_path):
        if not os.path.isdir(local_path):
            self.debug_print('本地目录 %s 不存在' % local_path)
            return
        """
        创建服务器目录
        """
        try:
            self.ftp.cwd(remote_path)  # 切换工作路径
        except Exception as e:
            base_dir, part_path = self.ftp.pwd(), remote_path.split('/')
            for p in part_path[1:-1]:
                base_dir = base_dir + p + '/'  # 拼接子目录
                try:
                    self.ftp.cwd(base_dir)  # 切换到子目录, 不存在则异常
                except Exception as e:
                    print('INFO:', e)
                    self.ftp.mkd(base_dir)  # 不存在创建当前子目录
        #self.ftp.cwd(remote_path)
        self.debug_print('切换至远程目录: %s' % self.ftp.pwd())

        local_name_list = os.listdir(local_path)
        self.debug_print('本地目录list: %s' % local_name_list)
        #self.debug_print('判断是否有服务器目录: %s' % os.path.isdir())

        for local_name in local_name_list:
            src = os.path.join(local_path, local_name)
            print("src路径=========="+src)
            if os.path.isdir(src):
                try:
                    self.ftp.mkd(local_name)
                except Exception as err:
                    self.debug_print("目录已存在 %s ,具体错误描述为：%s" % (local_name, err))
                self.debug_print("upload_file_tree()---> 上传目录： %s" % local_name)
                self.debug_print("upload_file_tree()---> 上传src目录： %s" % src)
                self.upload_file_tree(src, local_name)
            else:
                self.debug_print("upload_file_tree()---> 上传文件： %s" % local_name)
                self.upload_file(src, local_name)
        self.ftp.cwd("..")

    def close(self):
        self.debug_print("close()---> FTP退出")
        self.ftp.quit()
        self.log_file.close()

    # 打印日志
    def debug_print(self, s):
        self.write_log(s)

    def deal_error(self, e):
        log_str = '发生错误: %s' % e
        self.write_log(log_str)
        sys.exit()

    # 写日志
    def write_log(self, log_str):
        time_now = time.localtime()
        date_now = time.strftime("%Y-%m-%d %H:%M:%S", time_now)
        format_log_str = "%s ---> %s \n " % (date_now, log_str)
        print(format_log_str)
        self.log_file.write(format_log_str)

    def get_file_list(self, line):
        file_arr = self.get_file_name(line)
        # 去除  . 和  ..
        if file_arr[1] not in ['.', '..']:
            self.file_list.append(file_arr)

    def get_file_name(self, line):
        pos = line.rfind(':')
        while (line[pos] != ' '):
            pos += 1
        while (line[pos] == ' '):
            pos += 1
        file_arr = [line[0], line[pos:]]
        return file_arr


if __name__ == "__main__":
    my_ftp = MyFTP("192.168.0.27")
    #my_ftp.set_pasv(False)
    my_ftp.login("vdog", "123456")

    # # my_ftp.create_ftp_path("/10.6.8.181/evade_images/20201024/2250/3333/123.jpg")
    # ftp_path = "D:/monitor_images/10.6.8.181/evade_images/20200904/10.6.8.181_20200904_134527.217.jpg"
    # # print(ftp_path[:, ftp_path.rindex("/")])
    # print(ftp_path.rindex("/"))
    # # print()
    # dirs = ftp_path[17: ftp_path.rindex("/") + 1]
    # print(dirs)
    # my_ftp.create_ftp_path(dirs)

    while True:
        # 上传单个文件
        my_ftp.upload_file("D:/monitor_images/10.6.8.181/evade_images/20201023/10.6.8.181_20201023_110508.855.jpg", "/10.6.8.181/evade_images/20201023/10.6.8.181_20201023_110508.855.jpg")

        isSame = my_ftp.is_same_size("D:/monitor_images/10.6.8.181/evade_images/20201023/10.6.8.181_20201023_110508.855.jpg", "/10.6.8.181/evade_images/20201023/10.6.8.181_20201023_110508.855.jpg")
        if isSame == 1:
            break
        else:
            time.sleep(10)    # 上传失败后稍作延时重试
    my_ftp.close()