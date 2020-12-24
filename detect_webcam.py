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
import datetime
import hashlib
import numpy as np

from PIL import Image, ImageDraw, ImageFont
import colorsys
from common.config import normal_save_path, evade_save_path, ip, log, image_size, rtsp_url, evade_origin_save_path, imgCacheSize, imgNearSize, evade_video_path, start_hour, end_hour
from common.evadeUtil import evade_vote, judgeStatus, evade4new, calc_iou, gate_light_area_list, gate_area_list
from common.dateUtil import formatTimestamp
from common.dbUtil import saveManyDetails2DB, getMaxPersonID, saveFTPLog2DB
from common.Stack import Stack
from common.trackUtil import getUsefulTrack
from common.cleanUtil import cleaning_box
from common.FTPUtil import MyFTP
import threading

from utils.parser import get_config

from detector import build_detector
from deep_sort import build_tracker

warnings.filterwarnings('ignore')

'''
    本地视频模拟视频流
'''
def capture_video(video_path, frame_buffer, lock, imgCacheList, cacheLock):
    count = 0    # 标记当前帧数
    fo = open("read.txt", 'w', encoding='utf-8')

    if os.path.isfile(video_path):
        fo.write(video_path + "\n")
        fo.flush()
        vid = cv2.VideoCapture(video_path)
        if not vid.isOpened():
            raise IOError("Couldn't open webcam or video")

        while True:
            return_value, frame = vid.read()
            read_time = time.time()  # 读取时间
            if return_value is True:
                if count % 2 == 0:  # 表示每2帧接入一帧
                    count = 0
                    lock.acquire()
                    frame_buffer.push((read_time, frame))  # 用于跳帧识别的缓存
                    lock.release()
            cacheLock.acquire()
            imgCacheList.append((read_time, frame))  # 用于合成视频
            if len(imgCacheList) > imgCacheSize:  # 如果超长，则删除最前面的
                imgCacheList.remove(imgCacheList[0])
            cacheLock.release()
            time.sleep(0.5)
    else:
        for file in os.listdir(video_path):
            video_file = os.path.join(video_path, file)
            fo.write(video_file + "\n")
            fo.flush()

            vid = cv2.VideoCapture(video_file)
            if not vid.isOpened():
                raise IOError("Couldn't open webcam or video")

            while True:
                return_value, frame = vid.read()
                read_time = time.time()  # 读取时间
                if return_value is True:
                    if count % 2 == 0:  # 表示每2帧接入一帧
                        count = 0
                        lock.acquire()
                        frame_buffer.push((read_time, frame))  # 用于跳帧识别的缓存
                        lock.release()
                else:
                    break
                cacheLock.acquire()
                imgCacheList.append((read_time, frame))  # 用于合成视频
                if len(imgCacheList) > imgCacheSize:  # 如果超长，则删除最前面的
                    imgCacheList.remove(imgCacheList[0])
                cacheLock.release()
                time.sleep(0.5)




'''
    视频流读取线程：读取到自定义缓冲区
'''
def capture_thread(input_webcam, frame_buffer, lock, imgCacheList, cacheLock):
    if input_webcam == "0":
        input_webcam = int(0)
    print("capture_thread start: %s" % (input_webcam))
    log.logger.info("capture_thread start: %s" % (input_webcam))
    count = 0    # 标记当前帧数

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
        if return_value is True:
            read_time = time.time()  # 读取时间

            # 判断时间：只识别运营中的
            n_time = datetime.datetime.fromtimestamp(read_time)    # 时间戳转datetime
            start_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + start_hour, '%Y-%m-%d%H:%M')
            end_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + end_hour, '%Y-%m-%d%H:%M')

            if n_time >= start_time and n_time <= end_time:
                if count % 2 == 0:  # 表示每2帧接入一帧
                    count = 0
                    lock.acquire()
                    frame_buffer.push((read_time, frame))  # 用于跳帧识别的缓存
                    lock.release()
                cacheLock.acquire()
                imgCacheList.append((read_time, frame))  # 用于合成视频
                if len(imgCacheList) > imgCacheSize:  # 如果超长，则删除最前面的
                    imgCacheList.remove(imgCacheList[0])
                cacheLock.release()
                cv2.waitKey(1)  # delay ms
            else:
                continue
        else:
            time.sleep(0.5)  # 读取失败后直接重连没有任何意义
            vid = cv2.VideoCapture(input_webcam)
            print("读取失败, 已重连: %s" % (vid))
            log.logger.error("读取失败, 已重连: %s" % (vid))


def detect_thread(cfg, frame_buffer, lock, imgCacheList, cacheLock):
    # # 准备FTP服务器
    # my_ftp = MyFTP(ftp_ip)
    # # my_ftp.set_pasv(False)
    # my_ftp.login(ftp_username, ftp_password)

    use_cuda = torch.cuda.is_available()    # 是否用cuda
    curr_person_id = getMaxPersonID()       # 目前最大人物ID

    detector = build_detector(cfg, use_cuda=use_cuda)    # 构建检测器
    deepsort = build_tracker(cfg, use_cuda=use_cuda, n_start=curr_person_id)     # 构建追踪器
    class_names = detector.class_names              # 所有类别

    # Generate colors for drawing bounding boxes.
    hsv_tuples = [(x / len(class_names), 1., 1.)
                  for x in range(len(class_names))]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(
        map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)),
            colors))
    np.random.seed(10101)  # Fixed seed for consistent colors across runs.
    np.random.shuffle(colors)  # Shuffle colors to decorrelate adjacent classes.
    np.random.seed(None)  # Reset seed to default.

    font = ImageFont.truetype(font='font/FiraMono-Medium.otf',
                              size=np.floor(3e-2 * image_size[1] + 0.5).astype('int32'))  # 640*480
    thickness = (image_size[0] + image_size[1]) // 300

    personBoxDict = {}        # 每个人的人物框：{person_id: box左上右下}
    personForwardDict = {}    # 每个人的方向状态：{personid: 方向}，0无方向（新人）；1向上；2向下；3丢失（出域）
    personLocaDict = {}       # 每个人的位置：{personid: 位置}，0图像上半截；1图像下半截
    personIsCrossLine = {}    # 每个人是否过线：{personid: 是否过线}，0没过线；1过线

    following_list = []  # 尾随者list，(box, id)

    while True:
        try:
            if frame_buffer.size() > 0:
                read_t1 = time.time()  # 读取动作开始
                lock.acquire()
                curr_timestamp, frame = frame_buffer.get()  # 按序拿
                lock.release()

                print("=================== start a image reco %s ===================" % (formatTimestamp(curr_timestamp, ms=True)))
                log.logger.info("=================== start a image reco %s ===================" % (formatTimestamp(curr_timestamp, ms=True)))

                read_time = time.time() - read_t1  # 读取动作结束
                curr_time_path = formatTimestamp(curr_timestamp, format='%Y%m%d_%H%M%S', ms=True)

                detect_t1 = time.time()  # 检测动作开始

                # 先做检测
                # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)    # BGR转RGB，用于识别。这里转换移到detector()里做
                bbox_xyxy, cls_conf, cls_ids = detector(frame)    # 这里所有的检出，box格式均为：左上右下

                # 经过对原始框的预处理，现在：大人和小孩：左上宽高；物品：上左下右
                # 大人和小孩分开处理，这时已进行nms
                (adult_classes, adult_boxs, adult_scores), \
                (child_classes, child_boxs, child_scores), \
                (other_classes, other_boxs, other_scores) = cleaning_box(bbox_xyxy, cls_conf, cls_ids, class_names)

                # 再做追踪
                deepsort.update(frame, adult_classes, adult_boxs, adult_scores, child_classes, child_boxs, child_scores)

                # 这里出现bug：误检，只检出一个人，为什么tracker.tracks中有三个人
                # 原因：人走了，框还在
                # 解决办法：更新后的tracker.tracks与person_boxs再做一次iou，对于每个person_boxs，只保留与其最大iou的track

                trackList_adult = getUsefulTrack(adult_boxs, deepsort.tracker.tracks, "adult")
                trackList_child = getUsefulTrack(child_boxs, deepsort.tracker.tracks, "child")

                print("检测到：大人 %d %s, 小孩 %d %s" % (len(adult_boxs), adult_boxs, len(child_boxs), child_boxs))
                print("追踪到：大人 %d %s, 小孩 %d %s" % (len(trackList_adult), [track.to_tlbr() for track in trackList_adult],
                                                  len(trackList_child), [track.to_tlbr() for track in trackList_child]))
                log.logger.info("检测到：大人 %d %s, 小孩 %d %s" % (len(adult_boxs), adult_boxs, len(child_boxs), child_boxs))
                log.logger.info("追踪到：大人 %d %s, 小孩 %d %s" % (len(trackList_adult), [track.to_tlbr() for track in trackList_adult],
                                                  len(trackList_child), [track.to_tlbr() for track in trackList_child]))

                trackList = trackList_adult + trackList_child

                # 这里判定每个人的方向，及所在区域
                personForwardDict, personBoxDict, personLocaDict, personIsCrossLine = judgeStatus(trackList,
                                                                                                  personForwardDict,
                                                                                                  personBoxDict,
                                                                                                  personLocaDict,
                                                                                                  personIsCrossLine)

                # # 判定通行状态：0正常通过，1涉嫌逃票
                # # print("frame.shape:", frame.shape)    # frame.shape: (480, 640, 3)
                # flag, TrackContentList = evade_vote(trackList, other_classes, other_boxs, other_scores,
                #                                     frame.shape[0], personForwardDict, personBoxDict,
                #                                     personLocaDict, personIsCrossLine, curr_time_path)  # frame.shape, (h, w, c)
                log.logger.info("*** len(following_list): %d" % (len(following_list)))
                flag, TrackContentList, following_list = evade4new(trackList, other_classes, other_boxs, other_scores,
                                                                   frame.shape[0], personForwardDict, personBoxDict,
                                                                   personLocaDict, personIsCrossLine, curr_time_path,
                                                                   following_list)  # frame.shape, (h, w, c)
                log.logger.info("$$$ len(following_list): %d" % (len(following_list)))

                detect_time = time.time() - detect_t1  # 检测动作结束

                # if flag == "WARNING":
                if True:
                    # 标注（只对逃票情况做标注，正常情况不标注了）
                    # image = Image.fromarray(frame)  # 这里不用再转：已经是rgb了
                    image = Image.fromarray(frame[..., ::-1])  # bgr to rgb，转成RGB格式进行做标注
                    draw = ImageDraw.Draw(image)

                    for trackContent in TrackContentList:  # 标注人，track.state=0/1，都在tracker.tracks中
                        # bbox = trackContent.to_tlbr()  # 左上右下
                        bbox = trackContent.bbox
                        if trackContent.pass_distance == 0:
                            # label = '{} {:.2f} {} {}'.format(track.classes, track.score, track.track_id, track.state)
                            label = '{} {}'.format(trackContent.cls, trackContent.track_id)
                        else:
                            # label = '{} {:.2f} {} {} {}'.format(track.classes, track.score, track.track_id, track.state, track.pass_distance)
                            label = '{} {} {:.2f}'.format(trackContent.cls, trackContent.track_id, trackContent.pass_distance)
                        label_size = draw.textsize(label, font)

                        left, top, right, bottom = int(bbox.split("_")[0]), int(bbox.split("_")[1]), int(
                            bbox.split("_")[2]), int(bbox.split("_")[3])
                        top = max(0, np.floor(top + 0.5).astype('int32'))
                        left = max(0, np.floor(left + 0.5).astype('int32'))
                        bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
                        right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
                        print(label, (left, top), (right, bottom))
                        log.logger.info("%s, (%d, %d), (%d, %d)" % (label, left, top, right, bottom))

                        if top - label_size[1] >= 0:
                            text_origin = np.array([left, top - label_size[1]])
                        else:
                            text_origin = np.array([left, top + 1])

                        # My kingdom for a good redistributable image drawing library.
                        for i in range(thickness):
                            draw.rectangle(
                                [left + i, top + i, right - i, bottom - i],
                                outline=colors[class_names.index(trackContent.cls)])
                        draw.rectangle(
                            [tuple(text_origin), tuple(text_origin + label_size)],
                            fill=colors[class_names.index(trackContent.cls)])
                        draw.text(text_origin, label, fill=(0, 0, 0), font=font)

                    for (other_cls, other_box, other_score) in zip(other_classes, other_boxs,
                                                                   other_scores):  # 其他的识别，只标注类别和得分值
                        if other_cls in ['redLight', 'greenLight', 'yellowLight']:  # 闸机灯和门另外标注
                            # 逐个计算每个灯与标定的灯位置的iou，最大iou>0.45时才认为是真实的灯
                            top, left, bottom, right = other_box
                            curr_box = [left, top, right, bottom]  # 计算iou要求左上右下
                            iou_result = calc_iou(bbox1=[curr_box],
                                                  bbox2=gate_light_area_list)  # 行：检测到的灯区域序列；列：真实位置灯区域序列
                            for i in range(len(iou_result)):
                                maxiou = iou_result[i].max()  # 最大的iou
                                if maxiou > 0.45:  # 认为是真实的灯
                                    label = '{} {:.2f}'.format(other_cls, other_score)
                                    # print("label:", label)
                                    label_size = draw.textsize(label, font)

                                    top = max(0, np.floor(top + 0.5).astype('int32'))
                                    left = max(0, np.floor(left + 0.5).astype('int32'))
                                    bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
                                    right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
                                    print(label, (left, top), (right, bottom))
                                    log.logger.info("%s, (%d, %d), (%d, %d)" % (label, left, top, right, bottom))

                                    if top - label_size[1] >= 0:
                                        text_origin = np.array([left, top - label_size[1]])
                                    else:
                                        text_origin = np.array([left, top + 1])

                                    # My kingdom for a good redistributable image drawing library.
                                    for i in range(thickness):
                                        draw.rectangle(
                                            [left + i, top + i, right - i, bottom - i],
                                            outline=colors[class_names.index(other_cls)])
                                    draw.rectangle(
                                        [tuple(text_origin), tuple(text_origin + label_size)],
                                        fill=colors[class_names.index(other_cls)])
                                    draw.text(text_origin, label, fill=(0, 0, 0), font=font)
                        # elif other_cls in ['cloudGate', 'normalGate']:    # 闸机门用中心点过滤，而不是iou
                        #     top, left, bottom, right = other_box
                        #     centerx = (left + right) / 2
                        #     centery = (top + bottom) / 2
                        #     # print(centerx, centery)
                        #     print("当前闸机：", centerx, centery)
                        #
                        #     for gate_area in gate_area_list:
                        #         gleft, gtop, gright, gbottom = gate_area
                        #
                        #         # 检测到的在标定范围内，说明是真的闸机
                        #         if (centerx >= gleft and centerx <= gright) and (centery >= gtop and centery <= gbottom):
                        #             label = '{} {:.2f}'.format(other_cls, other_score)
                        #             # print("label:", label)
                        #             label_size = draw.textsize(label, font)
                        #
                        #             top = max(0, np.floor(top + 0.5).astype('int32'))
                        #             left = max(0, np.floor(left + 0.5).astype('int32'))
                        #             bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
                        #             right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
                        #             print(label, (left, top), (right, bottom))
                        #             log.logger.info("%s, (%d, %d), (%d, %d)" % (label, left, top, right, bottom))
                        #
                        #             if top - label_size[1] >= 0:
                        #                 text_origin = np.array([left, top - label_size[1]])
                        #             else:
                        #                 text_origin = np.array([left, top + 1])
                        #
                        #             # My kingdom for a good redistributable image drawing library.
                        #             for i in range(thickness):
                        #                 draw.rectangle(
                        #                     [left + i, top + i, right - i, bottom - i],
                        #                     outline=colors[class_names.index(other_cls)])
                        #             draw.rectangle(
                        #                 [tuple(text_origin), tuple(text_origin + label_size)],
                        #                 fill=colors[class_names.index(other_cls)])
                        #             draw.text(text_origin, label, fill=(0, 0, 0), font=font)
                        else:
                            label = '{} {:.2f}'.format(other_cls, other_score)
                            # print("label:", label)
                            label_size = draw.textsize(label, font)

                            top, left, bottom, right = other_box
                            top = max(0, np.floor(top + 0.5).astype('int32'))
                            left = max(0, np.floor(left + 0.5).astype('int32'))
                            bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
                            right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
                            print(label, (left, top), (right, bottom))
                            log.logger.info("%s, (%d, %d), (%d, %d)" % (label, left, top, right, bottom))

                            if top - label_size[1] >= 0:
                                text_origin = np.array([left, top - label_size[1]])
                            else:
                                text_origin = np.array([left, top + 1])

                            # My kingdom for a good redistributable image drawing library.
                            for i in range(thickness):
                                draw.rectangle(
                                    [left + i, top + i, right - i, bottom - i],
                                    outline=colors[class_names.index(other_cls)])
                            draw.rectangle(
                                [tuple(text_origin), tuple(text_origin + label_size)],
                                fill=colors[class_names.index(other_cls)])
                            draw.text(text_origin, label, fill=(0, 0, 0), font=font)
                    del draw

                    result = np.asarray(image)  # 这时转成np.ndarray后是rgb模式，out.write(result)保存为视频用
                    # bgr = rgb[..., ::-1]    # rgb转bgr
                    result = result[..., ::-1]  # 转成BGR做cv2.imwrite()用

                print(time.time() - read_t1)
                log.logger.info("%f" % (time.time() - read_t1))  # 标注结束

                ################ 批量入库 ################
                if len(TrackContentList) > 0:  # 只有有人，才进行入库，保存等操作
                    curr_time = formatTimestamp(curr_timestamp, ms=True)  # 当前时间按读取时间算，精确到毫秒
                    curr_date = formatTimestamp(curr_timestamp, format='%Y%m%d')

                    normal_time_path = normal_save_path + curr_date + "/"  # 正常图片，按天分目录
                    evade_time_path = evade_save_path + curr_date + "/"  # 逃票图片，标注后
                    evade_origin_time_path = evade_origin_save_path + curr_date + "/"  # 逃票原始图片
                    evade_video_time_path = evade_video_path + curr_date + "/"  # 逃票图片的上下文视频

                    # 分别创建目录
                    if os.path.exists(normal_time_path) is False:
                        os.makedirs(normal_time_path)
                    if os.path.exists(evade_time_path) is False:
                        os.makedirs(evade_time_path)
                    if os.path.exists(evade_origin_time_path) is False:
                        os.makedirs(evade_origin_time_path)
                    if os.path.exists(evade_video_time_path) is False:
                        os.makedirs(evade_video_time_path)

                    if flag == "NORMAL":  # 正常情况（20201029更新：正常情况和逃票小视频不保存了）
                        savefile = os.path.join(normal_time_path, ip + "_" + curr_time_path + ".jpg")
                        # status = cv2.imwrite(filename=savefile, img=result)  # cv2.imwrite()保存文件，路径不能有2个及以上冒号
                        status = False
                        print("时间: %s, 状态: %s, 文件: %s, 保存状态: %s" % (curr_time_path, flag, savefile, status))
                        log.logger.info("时间: %s, 状态: %s, 文件: %s, 保存状态: %s" % (curr_time_path, flag, savefile, status))
                    elif flag == "WARNING":  # 逃票情况
                        savefile = os.path.join(evade_time_path, ip + "_" + curr_time_path + ".jpg")
                        status = cv2.imwrite(filename=savefile, img=result)

                        # 只有检出逃票行为后，才将原始未标注的图片保存，便于以后更新模型
                        originfile = os.path.join(evade_origin_time_path, ip + "_" + curr_time_path + "-origin.jpg")
                        status2 = cv2.imwrite(filename=originfile, img=frame)

                        print("时间: %s, 状态: %s, 原始文件: %s, 保存状态: %s, 检后文件: %s, 保存状态: %s" % (
                            curr_time_path, flag, originfile, status2, savefile, status))
                        log.logger.warn("时间: %s, 状态: %s, 原始文件: %s, 保存状态: %s, 检后文件: %s, 保存状态: %s" % (
                            curr_time_path, flag, originfile, status2, savefile, status))

                        # 开始拼接视频（视频不拼接了，放到后端 录制+截取）
                        try:
                            cacheLock.acquire()

                            index = [i for i in range(len(imgCacheList)) if imgCacheList[i][0]==curr_timestamp][0]    # 拿到当前下标
                            start = max(0, index - imgNearSize)
                            end = min(len(imgCacheList), index + imgNearSize)
                            tmp = imgCacheList[start: end]
                            cacheLock.release()

                            t1 = time.time()
                            video_FourCC = 875967080
                            video_fps = 25
                            video_size = (frame.shape[1], frame.shape[0])
                            video_file = os.path.join(evade_video_time_path, ip + "_" + curr_time_path + ".mp4")

                            out = cv2.VideoWriter(video_file, video_FourCC, video_fps, video_size)
                            for t in tmp:
                                out.write(t[1])
                            out.release()

                            savevideo_time = time.time() - t1
                            print("视频保存完成: %s %s %s %s, 耗时: %.3f" % (video_file, start, index, end, savevideo_time))
                            log.logger.info("视频保存完成: %s %s %s %s, 耗时: %.3f" % (video_file, start, index, end, savevideo_time))
                        except ValueError as e:
                            cacheLock.release()
                            print("当前图片不存在于缓存中: %s" % (traceback.format_exc()))
                            log.logger.error("当前图片不存在于缓存中: %s" % (traceback.format_exc()))

                        print("视频保存完成: %s" % (video_file))
                        log.logger.info("视频保存完成: %s" % (video_file))
                    else:  # 没人的情况
                        print("时间: %s, 状态: %s" % (curr_time_path, flag))
                        log.logger.info("时间: %s, 状态: %s" % (curr_time_path, flag))
                    saveManyDetails2DB(ip=ip,
                                       curr_time=curr_time,
                                       savefile=savefile,
                                       read_time=read_time,
                                       detect_time=detect_time,
                                       TrackContentList=TrackContentList)  # 批量入库
                print("******************* end a image reco %s *******************" % (formatTimestamp(time.time(), ms=True)))
                log.logger.info("******************* end a image reco %s *******************" % (formatTimestamp(time.time(), ms=True)))
        except Exception as e:
            traceback.print_exc()
            log.logger.error(traceback.format_exc())
    cv2.destroyAllWindows()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_detection", type=str, default="./configs/yolov5s-evade.yaml")
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

    # 自定义识别缓冲区
    frame_buffer = Stack(30 * 5)
    lock = threading.RLock()    # RLock()，多重锁，同一线程中可多次acquire()
    cacheLock = threading.RLock()

    imgCacheList = []  # 原图缓存队列，用做视频拼接

    # input_path = "D:/logs/10.6.8.181_20201104_171711.558.mp4"
    input_path = "D:/logs/"
    # input_path = 0
    t1 = threading.Thread(target=capture_thread, args=(rtsp_url, frame_buffer, lock, imgCacheList, cacheLock))
    t1.start()
    # t1 = threading.Thread(target=capture_video, args=(input_path, frame_buffer, lock, imgCacheList, cacheLock))
    # t1.start()
    t2 = threading.Thread(target=detect_thread, args=(cfg, frame_buffer, lock, imgCacheList, cacheLock))
    t2.start()