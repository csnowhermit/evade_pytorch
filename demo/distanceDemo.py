import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


df_distance = pd.read_csv('d:/workspace/DA/distance.csv')
# # df_person = df_person.set_index('image_id')
df_distance.insert(0, 'New_ID', range(0, 0 + len(df_distance)))

up_distance = 1080 * 0.6
down_distance = 1080 * 0.2
print(up_distance, down_distance)

df_holdbaby = df_distance[df_distance["types"] == "holdbaby"]
df_evade = df_distance[df_distance["types"] == "evade"]

# holdbaby = df_holdbaby['distance']
# evade = df_evade['distance']

plt.figure(figsize=(40, 10))
plt.scatter(df_evade['New_ID'], df_evade['distance'], marker = 'x',color = 'red', s = 40 ,label = 'evade')
plt.scatter(df_holdbaby['New_ID'], df_holdbaby['distance'], marker = '+', color = 'blue', s = 40, label = 'holdbaby')
plt.legend(loc = 'best')    # 设置 图例所在的位置 使用推荐位置
plt.show()

# 按比例算
df_holdbaby['distance_rate'] = df_holdbaby['distance'] / 1080
df_evade['distance_rate'] = df_evade['distance'] / 1080

plt.figure(figsize=(40, 10))
plt.scatter(df_evade['New_ID'], df_evade['distance_rate'], marker = 'x',color = 'red', s = 40 ,label = 'evade')
plt.scatter(df_holdbaby['New_ID'], df_holdbaby['distance_rate'], marker = '+', color = 'blue', s = 40, label = 'holdbaby')
plt.legend(loc = 'best')    # 设置 图例所在的位置 使用推荐位置
plt.show()
