import numpy as np
import pandas as pd
import matplotlib.pyplot as plt    # 用pyplt画

df_person = pd.read_csv('D:/workspace/DA/person.csv')
# df_person = df_person.set_index('image_id')
df_person.insert(0, 'New_ID', range(0, 0 + len(df_person)))

# 左侧通道的区域范围：0_0_155_360
passway_area = (float(0/640), float(155/640))
left_begin = float(0/640)
left_end = float(155/640)
print(left_begin, left_end)

# 计算每个人物框的宽高
df_person['pwidth_ratio'] = (df_person['right'] - df_person['left'])/df_person['width']
df_person['pheight_ratio'] = (df_person['bottom'] - df_person['top'])/df_person['height']
df_person['width_over_height'] = df_person['pwidth_ratio'] / df_person['pheight_ratio']    # 宽高比
df_person['area_ratio'] = df_person['pwidth_ratio'] * df_person['pheight_ratio']         # 面积比

df_person['centerx'] = ((df_person['right'] + df_person['left'])/2) / df_person['width']    # 中心点x坐标

df_left = df_person[(df_person['centerx'] >= left_begin) & (df_person['centerx'] <= left_end)]    # 筛选出左侧通道的

# 检验df_left中是否有混入其他通道的
tmp = df_left[df_left['centerx'] > left_end]
print("tmp:", tmp)

# 分别筛选出大人和小孩的
df_adult = df_left[df_left['cls_name'] == 'adult']
df_child = df_left[df_left['cls_name'] == 'child']

df_adult.aggregate([min, max, np.mean, np.std, np.median])    # 大人的均值，标准差，中位数
df_child.aggregate([min, max, np.mean, np.std, np.median])    # 小孩的均值，标准差，中位数

# df_left.to_csv("./left.csv")

# 去极值：分位数去极值法
def filter_extreme_percent(series, min=0.025, max=0.975):
    series = series.sort_values()
    q = series.quantile([min, max])
    print("q:", q.iloc[0], q.iloc[1])
    return np.clip(series, q.iloc[0], q.iloc[1])

# 先考虑宽高比
percentile_adult = filter_extreme_percent(df_adult['width_over_height'])    # 对大人去极值
percentile_child = filter_extreme_percent(df_child['width_over_height'])    # 对小孩去极值

adult_width_over_height = df_adult['width_over_height']
child_width_over_height = df_child['width_over_height']

plt.figure(figsize=(40, 10))
plt.scatter(df_adult['New_ID'], df_adult['width_over_height'], marker = 'x',color = 'red', s = 40 ,label = 'adult')
plt.scatter(df_child['New_ID'], df_child['width_over_height'], marker = '+', color = 'blue', s = 40, label = 'child')

plt.legend(loc = 'best')    # 设置 图例所在的位置 使用推荐位置
plt.show()

# 再考虑面积比率
percentile_adult = filter_extreme_percent(df_adult['area_ratio'])    # 对大人去极值
percentile_child = filter_extreme_percent(df_child['area_ratio'])    # 对小孩去极值

adult_area_ratio = df_adult['area_ratio']
child_area_ratio = df_child['area_ratio']

plt.figure(figsize=(40, 10))
plt.scatter(df_adult['New_ID'], df_adult['area_ratio'], marker = 'x',color = 'red', s = 40 ,label = 'adult')
plt.scatter(df_child['New_ID'], df_child['area_ratio'], marker = '+', color = 'blue', s = 40, label = 'child')

plt.legend(loc = 'best')    # 设置 图例所在的位置 使用推荐位置
plt.show()

# 推演：用[0.4, 0.7]的宽高比过滤出小孩后，面积范围能不能落在[0, 0.02之间]？
woh = df_left[(df_left['width_over_height'] >= 0.4) & (df_left['width_over_height'] <= 0.7)]
print(woh.head())

woh_adult = woh[woh['cls_name'] == 'adult']
woh_child = woh[woh['cls_name'] == 'child']

plt.figure(figsize=(40, 10))
plt.scatter(woh_adult['New_ID'], woh_adult['area_ratio'], marker = 'x',color = 'red', s = 40 ,label = 'adult')
plt.scatter(woh_child['New_ID'], woh_child['area_ratio'], marker = '+', color = 'blue', s = 40, label = 'child')

plt.legend(loc = 'best')    # 设置 图例所在的位置 使用推荐位置
plt.show()

# 再看其他宽高比区间的，是不是全是大人了？
woh = df_left[(df_left['width_over_height'] < 0.4) | (df_left['width_over_height'] > 0.7)]
woh.head()

woh_adult = woh[woh['cls_name'] == 'adult']
woh_child = woh[woh['cls_name'] == 'child']

plt.figure(figsize=(40, 10))
plt.scatter(woh_adult['New_ID'], woh_adult['area_ratio'], marker = 'x',color = 'red', s = 40 ,label = 'adult')
plt.scatter(woh_child['New_ID'], woh_child['area_ratio'], marker = '+', color = 'blue', s = 40, label = 'child')

plt.legend(loc = 'best')    # 设置 图例所在的位置 使用推荐位置
plt.show()