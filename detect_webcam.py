#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import os
import argparse
from timeit import time
import warnings
import cv2
import torch
import traceback
import hashlib
import numpy as np

from PIL import Image, ImageDraw, ImageFont
import colorsys
from common.config import normal_save_path, evade_save_path, ip, log, image_size, rtsp_url, evade_origin_save_path, imgCacheSize, imgNearSize, evade_video_path
from common.evadeUtil import evade_vote
from common.dateUtil import formatTimestamp
from common.dbUtil import saveManyDetails2DB, getMaxPersonID
from common.Stack import Stack
from common.trackUtil import getUsefulTrack
import threading

from utils.parser import get_config

from detector import build_detector
from deep_sort import build_tracker

warnings.filterwarnings('ignore')


'''
    视频流读取线程：读取到自定义缓冲区
'''
def capture_thread(input_webcam, frame_buffer, lock, imgCacheList, md5List):
    if input_webcam == "0":
        input_webcam = int(0)
    print("capture_thread start: %s" % (input_webcam))
    log.logger.info("capture_thread start: %s" % (input_webcam))

    # vid = cv2.VideoCapture(input_webcam)
    # if not vid.isOpened():
    #     raise IOError("Couldn't open webcam or video")

    # 循环，直到打开连接之后
    while True:
        vid = cv2.VideoCapture(input_webcam)
        if vid.isOpened() is False:
            time.sleep(0.5)  # 读取失败后直接重连没有任何意义
            vid = cv2.VideoCapture(input_webcam)
            print("Couldn't open webcam or video, 已重连: %s" % (vid))
            log.logger.error("Couldn't open webcam or video, 已重连: %s" % (vid))
        if vid.isOpened():
            print("vid.isOpened() is True: %s" % (vid))
            log.logger.info("vid.isOpened() is True: %s" % (vid))
            break

    while True:
        try:
            return_value, frame = vid.read()
        except Exception as e:
            time.sleep(0.5)    # 读取失败后直接重连没有任何意义
            vid = cv2.VideoCapture(input_webcam)
            print("Exception: %s, \n 已重连: %s" % (traceback.format_exc(), vid))
            log.logger.error("Exception: %s, \n 已重连: %s" % (traceback.format_exc(), vid))
        except OSError as e:
            time.sleep(0.5)  # 读取失败后直接重连没有任何意义
            vid = cv2.VideoCapture(input_webcam)
            print("OSError: %s, \n 已重连: %s" % (traceback.format_exc(), vid))
            log.logger.error("OSError: %s, \n 已重连: %s" % (traceback.format_exc(), vid))
        if return_value is not True:
            time.sleep(0.5)  # 读取失败后直接重连没有任何意义
            vid = cv2.VideoCapture(input_webcam)
            print("读取失败, 已重连: %s" % (vid))
            log.logger.error("读取失败, 已重连: %s" % (vid))
        lock.acquire()
        frame_buffer.push(frame)    # 用于跳帧识别的缓存

        try:
            imgCacheList.append(frame)  # 用来生成截取视频的缓存
            sign = hashlib.md5(frame).hexdigest()
            md5List.append(sign)  # 图片的签名值
            if len(imgCacheList) > imgCacheSize:  # 如果超长，则删除最前面的
                imgCacheList.remove(imgCacheList[0])
            if len(md5List) > imgNearSize:
                md5List.remove(md5List[0])
        except TypeError as e:
            print("视频序列准备失败: %s" % (traceback.format_exc()))
            log.logger.error("视频序列准备失败: %s" % (traceback.format_exc()))
            pass
        except Exception as e:
            print("视频序列准备失败: %s" % (traceback.format_exc()))
            log.logger.error("视频序列准备失败: %s" % (traceback.format_exc()))
            pass

        lock.release()
        cv2.waitKey(25)    # delay 25ms

def detect_thread(cfg, frame_buffer, lock, imgCacheList, md5List):
    use_cuda = torch.cuda.is_available()    # 是否用cuda
    detector = build_detector(cfg, use_cuda=use_cuda)    # 构建检测器
    deepsort = build_tracker(cfg, use_cuda=use_cuda)     # 构建追踪器
    class_names = detector.class_names              # 所有类别

    while True:
        try:
            if frame_buffer.size() > 0:
                read_t1 = time.time()  # 读取动作开始
                lock.acquire()
                frame = frame_buffer.pop()  # 每次拿最新的
                lock.release()

                print("=================== start a image reco %s ===================" % (
                    formatTimestamp(time.time(), ms=True)))
                log.logger.info("=================== start a image reco %s ===================" % (
                    formatTimestamp(time.time(), ms=True)))

                read_time = time.time() - read_t1  # 读取动作结束
                detect_t1 = time.time()  # 检测动作开始

                im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)    # BGR转RGB，用于识别

                bbox_xywh, cls_conf, cls_ids = detector(im)    # 检测
                print(bbox_xywh, cls_conf, cls_ids)  # 框，置信度，类别id



        except Exception as e:
            log.logger.error(traceback.format_exc())
    cv2.destroyAllWindows()



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_detection", type=str, default="./configs/yolov3.yaml")
    parser.add_argument("--config_deepsort", type=str, default="./configs/deep_sort.yaml")
    # parser.add_argument("--ignore_display", dest="display", action="store_false", default=True)
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--frame_interval", type=int, default=1)
    parser.add_argument("--display_width", type=int, default=800)
    parser.add_argument("--display_height", type=int, default=600)
    parser.add_argument("--save_path", type=str, default="./output/")
    parser.add_argument("--cpu", dest="use_cuda", action="store_false", default=True)
    parser.add_argument("--camera", action="store", dest="cam", type=int, default="-1")
    return parser.parse_args()

if __name__ == '__main__':
    # 配置项
    args = parse_args()
    cfg = get_config()
    cfg.merge_from_file(args.config_detection)
    cfg.merge_from_file(args.config_deepsort)

    # 自定义十四别缓冲区
    frame_buffer = Stack(30 * 5)
    lock = threading.RLock()

    imgCacheList = []  # 原图缓存队列，用做视频拼接
    md5List = []  # 原图缓存队列中每帧的md5值
    # input_path = "E:/BaiduNetdiskDownload/2020-04-14/10.6.8.181_01_20200414185039477.mp4"
    # input_path = 0
    t1 = threading.Thread(target=capture_thread, args=(0, frame_buffer, lock, imgCacheList, md5List))
    t1.start()
    t2 = threading.Thread(target=detect_thread, args=(cfg, frame_buffer, lock, imgCacheList, md5List))
    t2.start()