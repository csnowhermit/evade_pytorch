import os
import time
import signal
import resource    # win10下暂没找到这个包
import psutil
from multiprocessing import Pool, cpu_count

'''
    限制资源占用工具
'''

def limit_cpu():
    p = psutil.Process(os.getpid())
    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

def time_exceeded(signo, frame):
    print("Time's up!")
    raise SystemExit(1)


def set_max_runtime(seconds):
    # Install the signal handler and set a resource limit
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, hard))
    signal.signal(signal.SIGXCPU, time_exceeded)

if __name__ == '__main__':
    # pool = Pool(None, limit_cpu())
    # while True:
    #     time.sleep(0.2)
    set_max_runtime(15)
    while True:
        pass
