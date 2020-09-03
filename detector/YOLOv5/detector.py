import cv2
import numpy as np
import torch

from .utils.utils import *
from .utils.datasets import *


class YOLOv5(object):
    def __init__(self, weightfile, namesfile, agnostic_nms, augment, conf_thres, half, img_size=640, iou_thres=0.45, opt_classes=None,
                 is_xywh=False, use_cuda=True):
        # 常量
        self.agnostic_nms = agnostic_nms
        self.augment = augment
        self.conf_thres = conf_thres
        self.half = half and use_cuda  # half precision only supported on CUDA   # 半精度
        self.size = img_size
        self.iou_thres = iou_thres
        self.use_cuda = use_cuda
        self.is_xywh = is_xywh
        self.class_names = self.load_class_names(namesfile)
        self.num_classes = len(self.class_names)
        self.opt_classes = opt_classes

        # 网络定义
        self.device = torch.device('cuda:0' if use_cuda else 'cpu')
        self.model = torch.load(weightfile, map_location=self.device)['model']
        self.model.to(self.device).eval()    # 把模型放到指定设备上
        if self.half:
            self.model.half()


    def __call__(self, ori_img):
        # img to tensor
        assert isinstance(ori_img, np.ndarray), "input must be a numpy array!"

        # img = cv2.resize(ori_img, (self.size, self.size))    # yolov5之前这么做resize
        # # 实际中，许多图片长宽比不同，直接cv2.resize()的话，两端的黑边大小都不同，而如果填充的较多，存在信息荣誉，影响推理速度
        # Padded resize
        img = letterbox(ori_img, new_shape=self.size)[0]

        # Convert
        img = img[:, :, ::-1].transpose(2, 0, 1)    # BGR转RGB，channel first
        img = np.ascontiguousarray(img)

        img = torch.from_numpy(img).to(self.device)       # 将图像放到指定设备上
        img = img.half() if self.half else img.float()    # uint8 to fp16/32
        img /= 255.0    # 归一化
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        pred = self.model(img, augment=self.augment)[0]

        if self.half:
            pred = pred.float()

        # Apply NMS
        pred = non_max_suppression(pred, self.conf_thres, self.iou_thres,
                                   fast=True, classes=self.opt_classes, agnostic=self.agnostic_nms)

        for i, det in enumerate(pred):    # 逐个处理每个检测结果
            if det is not None and len(det):
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], ori_img.shape).round()    # 映射到原图上

                # for *xyxy, conf, cls in det:
                #     if self.is_xywh:
                #         # bbox x y w h
                #         box = xyxy2xywh(xyxy)  # 转为 centerx, centery, width, height
                #     bbox.append(xyxy)
                #     cls_conf.append(conf)
                #     cls_ids.append(int(cls))
                bbox = det[:, :4]       # 拿前4列
                if self.is_xywh:    # 默认不用转为 centerx, centery, width, height
                    bbox = xyxy2xywh(bbox)
                cls_conf = det[:, 4]    # 拿第5列
                cls_ids = det[:, 5].int()     # 拿第6列
            else:    # 未检测到的，用空容器返回
                bbox = torch.FloatTensor([]).reshape([0, 4])
                cls_conf = torch.FloatTensor([])
                cls_ids = torch.LongTensor([])

        return bbox.cpu().detach().numpy(), cls_conf.cpu().detach().numpy(), cls_ids.cpu().detach().numpy()    # 放到cpu上才能转numpy()

    def load_class_names(self, namesfile):
        with open(namesfile, 'r', encoding='utf8') as fp:
            class_names = [line.strip() for line in fp.readlines()]
        return class_names