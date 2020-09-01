import cv2
import numpy as np
import torch

from .utils.utils import *


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
        img = ori_img.astype(np.float) / 255.

        img = cv2.resize(img, (self.size, self.size))
        img = torch.from_numpy(img).float().permute(2, 0, 1).unsqueeze(0)
        pred = self.model(img)[0]

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

        return bbox.detach().numpy(), cls_conf.detach().numpy(), cls_ids.detach().numpy()

    def load_class_names(self, namesfile):
        with open(namesfile, 'r', encoding='utf8') as fp:
            class_names = [line.strip() for line in fp.readlines()]
        return class_names