import os
import time
import schedule
import zipfile
import shutil
from common.dateUtil import formatTimestamp, getAppointDate
from common.config import ip, ftp_ip, ftp_username, ftp_password
from common.compressionUtil import writeAllFileToZip
from common.FTPUtil import MyFTP
from common.dbUtil import saveFTPLog2DB

'''
    ETL终端：定期扫描指定目录，压缩并上传到服务器
'''

src_base = ['D:/monitor_images/%s/evade_images/' % (ip),
            'D:/monitor_images/%s/evade_origin_images/' % (ip),
            'D:/monitor_images/%s/evade_video/' % (ip),
            'D:/monitor_images/%s/normal_images/' % (ip)]

ftp_base = ['/%s/evade_images/' % (ip),
            '/%s/evade_origin_images/' % (ip),
            '/%s/evade_video/' % (ip),
            '/%s/normal_images/' % (ip)]

'''
    压缩并上传文件
'''
def compress(n=1):
    ddate = getAppointDate(n)
    pendingList = []

    for src, target in zip(src_base, ftp_base):
        absDir = os.path.join(src, ddate)    # 要压缩的目录
        zipTargetFile = os.path.join(src, ddate + ".zip")    # 压缩后的目录
        ftpTargetFile = os.path.join(target, ddate + ".zip")    # 上传到FTP的全路径
        print(absDir, zipTargetFile, ftpTargetFile)
        pendingList.append((absDir, zipTargetFile, ftpTargetFile))

        # 准备压缩
        zipFile = zipfile.ZipFile(zipTargetFile, 'w', zipfile.ZIP_DEFLATED)
        writeAllFileToZip(absDir, zipFile)    # 压缩

    # 准备上传到服务器
    my_ftp = MyFTP(ftp_ip)
    # my_ftp.set_pasv(False)
    my_ftp.login(ftp_username, ftp_password)
    for (absDir, zipTargetFile, ftpTargetFile) in pendingList:
        while True:
            # 上传单个文件
            my_ftp.upload_file(zipTargetFile, ftpTargetFile)

            isSame = my_ftp.is_same_size(zipTargetFile, ftpTargetFile)
            if isSame == 1:    # 上传成功
                saveFTPLog2DB(zipTargetFile, ftpTargetFile, isSame)    # 保存每个文件的上传记录
                break
            else:
                saveFTPLog2DB(zipTargetFile, ftpTargetFile, isSame)  # 上传失败的也保存日志
                time.sleep(10)  # 上传失败后稍作延时重试
    my_ftp.close()
    # # 上传完成之后将本地文件删除
    # for (absDir, zipTargetFile, ftpTargetFile) in pendingList:
    #     shutil.rmtree(absDir)
    #     os.remove(zipTargetFile)

schedule.every().day.at("09:46").do(compress, 3)

if __name__ == '__main__':
    while True:
        schedule.run_pending()
        time.sleep(1)

