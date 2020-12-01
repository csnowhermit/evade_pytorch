from .YOLOv3 import YOLOv3
from .YOLOv5 import YOLOv5


__all__ = ['build_detector']

def build_detector(cfg, use_cuda):
    return YOLOv3(cfg.YOLOV3.CFG, cfg.YOLOV3.WEIGHT, cfg.YOLOV3.CLASS_NAMES,
                    score_thresh=cfg.YOLOV3.SCORE_THRESH, nms_thresh=cfg.YOLOV3.NMS_THRESH,
                    is_xywh=False, use_cuda=use_cuda)
    # return YOLOv5(weightfile=cfg.YOLOV5.WEIGHT, namesfile=cfg.YOLOV5.CLASS_NAMES,
    #               agnostic_nms=cfg.YOLOV5.agnostic_nms, augment=cfg.YOLOV5.augment,
    #               conf_thres=cfg.YOLOV5.conf_thres, half=cfg.YOLOV5.half, img_size=cfg.YOLOV5.img_size,
    #               iou_thres=cfg.YOLOV5.iou_thres, opt_classes=None if cfg.YOLOV5.opt_classes == "None" else cfg.YOLOV5.opt_classes,
    #               is_xywh=False, use_cuda=use_cuda)

