#!/usr/local/bin/python3
import os
import zipfile

'''
    图像压缩
    :param absDir 要压缩的目录
    :param zipFile 压缩后得到的文件
'''
def writeAllFileToZip(absDir, zipFile):
    i = 0
    for f in os.listdir(absDir):
        i += 1
        absFile = os.path.join(absDir, f)  # 子文件的绝对路径
        zipFile.write(absFile)
        if i % 10000 == 0:
            print("\t compressing:", i)
    print("\t compressing:", i)
    return 0