#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib

'''
    计算文件MD5值
'''

if __name__ == '__main__':
    file_name = "D:/workspace/workspace_python/deepsort_yolo3_evade.zip"
    with open(file_name, 'rb') as fp:
        data = fp.read()
    file_md5= hashlib.md5(data).hexdigest()
    print(file_md5)     # ac3ee699961c58ef80a78c2434efe0d0