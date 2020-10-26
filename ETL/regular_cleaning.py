import os
import sys
import time
import shutil
import schedule
import traceback

base_path = "D:/workspace/workspace_python/evade_pytorch"
sys.path.append(base_path)
from common.config import ip, ftp_ip, ftp_username, ftp_password
from common.dateUtil import getAppointDate
from common.dbUtil import getFileStatusInFTP, saveFTPLog2DB
from common.FTPUtil import MyFTP
from common.Logger import Logger

'''
    定期清理终端保存的文件，清理前和数据库比对，一致则清除
'''

# 日志
logfile = 'D:/evade_logs/rcleaning_%s.log' % ip
log = Logger(logfile, level='info', backCount=3)    # 只保留3天的日志

src_base = ['D:/monitor_images/%s/evade_images/' % (ip),
            'D:/monitor_images/%s/evade_origin_images/' % (ip),
            'D:/monitor_images/%s/evade_video/' % (ip),
            'D:/monitor_images/%s/normal_images/' % (ip)]

ftp_base = ['/%s/evade_images/' % (ip),
            '/%s/evade_origin_images/' % (ip),
            '/%s/evade_video/' % (ip),
            '/%s/normal_images/' % (ip)]

'''
    与服务器上文件比对，并删除
'''
def compare2FTPAndCleaning(n=1):
    ddate = getAppointDate(n)
    print("开始清理: %s" % (ddate))
    log.logger.info("开始清理: %s" % (ddate))

    # 准备上传到服务器
    my_ftp = MyFTP(ftp_ip)
    # my_ftp.set_pasv(False)
    my_ftp.login(ftp_username, ftp_password)

    for src_type, ftp_type in zip(src_base, ftp_base):
        src_path = os.path.join(src_type, ddate)
        for imgfile in os.listdir(src_path):
            try:
                # print(os.path.join(src_path, imgfile))    # 直接做join时两段路径是\连接的，这样在库中查不出来
                imgpath = "%s/%s" % (src_path, imgfile)
                num = getFileStatusInFTP(imgpath)
                # print(imgpath)

                ftp_dir = os.path.join(ftp_type, ddate)
                ftpTargetFile = os.path.join(ftp_dir, imgfile)
                # print("\t", ftpTargetFile)

                if num > 0:
                    # 说明有成功上传，本地文件可以删了
                    os.remove(imgpath)
                    print("已删除本地文件: %s" % (imgpath))
                    log.logger.info("已删除本地文件: %s" % (imgpath))
                else:
                    # 说明未成功上传过，先上传，成功后再删除
                    while True:
                        my_ftp.create_ftp_path(ftp_dir + "/")
                        # 上传单个文件
                        my_ftp.upload_file(imgpath, ftpTargetFile)

                        isSame = my_ftp.is_same_size(imgpath, ftpTargetFile)
                        if isSame == 1:  # 上传成功
                            saveFTPLog2DB(imgpath, ftpTargetFile, isSame)  # 保存每个文件的上传记录
                            print("服务器文件缺失, 已补发: 本地文件: %s, 远端文件: %s" % (imgpath, ftpTargetFile))
                            log.logger.info("服务器文件缺失, 已补发: 本地文件: %s, 远端文件: %s" % (imgpath, ftpTargetFile))
                            time.sleep(0.5)
                            os.remove(imgpath)  # 上传成功后删除
                            print("已删除本地文件: %s" % (imgpath))
                            log.logger.info("已删除本地文件: %s" % (imgpath))
                            break
                        else:
                            saveFTPLog2DB(imgpath, ftpTargetFile, isSame)  # 上传失败的也保存日志
                            print("服务器文件缺失, 补发失败, 10s后重试: 本地文件: %s, 远端文件: %s" % (imgpath, ftpTargetFile))
                            log.logger.warn("服务器文件缺失, 补发失败, 10s后重试: 本地文件: %s, 远端文件: %s" % (imgpath, ftpTargetFile))
                            time.sleep(10)  # 上传失败后稍作延时重试
            except Exception as e:
                print("校验删除出错: %s" % (traceback.format_exc()))
                log.logger.warn("校验删除出错: %s" % (traceback.format_exc()))


    for src_type in src_base:
        try:
            src_path = os.path.join(src_type, ddate)
            # 如果当前目录为空，则删除该目录
            if not os.listdir(src_path):
                # os.remove(src_path + "/")
                shutil.rmtree(src_path)
                print("已删除空目录: %s" % (src_path))
                log.logger.info("已删除空目录: %s" % (src_path))
        except Exception as e:
            print("删除空目录出错: %s" % (traceback.format_exc()))
            log.logger.warn("删除空目录出错: %s" % (traceback.format_exc()))
    print("数据清理完成: %s" % (ddate))
    log.logger.info("数据清理完成: %s" % (ddate))
    my_ftp.close()

# schedule.every().day.at("13:41").do(compare2FTPAndCleaning, 0)

if __name__ == '__main__':
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)
    compare2FTPAndCleaning(0)