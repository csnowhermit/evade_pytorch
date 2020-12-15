import numpy as np
import pandas as pd
import matplotlib.pyplot as plt    # 用pyplt画

df_person = pd.read_csv('D:/workspace/DA/person.csv')
# df_person = df_person.set_index('image_id')
df_person.insert(0, 'New_ID', range(0, 0 + len(df_person)))

# 中间通道的区域范围：235_0_450_360
passway_area = (float(235/640), float(450/640))
mid_begin = float(235/640)
mid_end = float(450/640)
print(mid_begin, mid_end)

# 计算每个人物框的宽高
df_person['pwidth_ratio'] = (df_person['right'] - df_person['left'])/df_person['width']
df_person['pheight_ratio'] = (df_person['bottom'] - df_person['top'])/df_person['height']
df_person['width_over_height'] = df_person['pwidth_ratio'] / df_person['pheight_ratio']    # 宽高比
df_person['area_ratio'] = df_person['pwidth_ratio'] * df_person['pheight_ratio']         # 面积比

df_person['centerx'] = ((df_person['right'] + df_person['left'])/2) / df_person['width']

df_mid = df_person[(df_person['centerx'] >= mid_begin) & (df_person['centerx'] <= mid_end)]    # 过滤出中间通道的

df_adult = df_mid[df_mid['cls_name'] == 'adult']
df_child = df_mid[df_mid['cls_name'] == 'child']

df_adult.aggregate([min, max, np.mean, np.std, np.median])    # 大人的均值，标准差，中位数
df_child.aggregate([min, max, np.mean, np.std, np.median])    # 小孩的均值，标准差，中位数

# 去极值：分位数去极值法
def filter_extreme_percent(series, min=0.025, max=0.975):
    series = series.sort_values()
    q = series.quantile([min, max])
    print("q:", q.iloc[0], q.iloc[1])
    return np.clip(series, q.iloc[0], q.iloc[1])

# 面积比率
percentile_adult = filter_extreme_percent(df_adult['area_ratio'])    # 对大人去极值
percentile_child = filter_extreme_percent(df_child['area_ratio'])    # 对小孩去极值

adult_area_ratio = df_adult['area_ratio']
child_area_ratio = df_child['area_ratio']

plt.figure(figsize=(40, 10))
plt.scatter(df_adult['New_ID'], df_adult['area_ratio'], marker = 'x',color = 'red', s = 40 ,label = 'adult')
plt.scatter(df_child['New_ID'], df_child['area_ratio'], marker = '+', color = 'blue', s = 40, label = 'child')

plt.legend(loc = 'best')    # 设置 图例所在的位置 使用推荐位置

plt.show()

