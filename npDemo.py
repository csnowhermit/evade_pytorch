import numpy as np

det = np.array([[11, 12, 13, 14, 15, 16],
                [21, 22, 23, 24, 25, 26],
                [31, 32, 33, 34, 35, 36],
                [41, 42, 43, 44, 45, 46]])

bbox = det[:, :4]
print(bbox)
cls_conf = det[:, 4]
print(cls_conf)
cls_ids = det[:, 5]
print(cls_ids)
