import os

video_path = "D:/logs/"
fo = open("read.txt", 'w', encoding='utf-8')

for file in os.listdir(video_path):
    video_full_path = os.path.join(video_path, file)
    fo.write(video_full_path + "\n")
    fo.flush()
    # print(video_full_path)
    # target_filename = video_full_path.replace(" ", '-')
    # os.rename(video_full_path, target_filename)
    os.system("python detect_video.py --input %s" % video_full_path)