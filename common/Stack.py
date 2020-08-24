import os

'''
    自定义栈，解决视频消费速度赶不上生成速度的问题。
    原因：opencv自带的缓冲区无提供api供操作
'''

class Stack:
    def __init__(self, stack_size):
        self.items = []
        self.stack_size = stack_size

    def is_empty(self):
        return len(self.items) == 0

    def pop(self):
        return self.items.pop()

    def peek(self):
        if not self.isEmpty():
            return self.items[len(self.items) - 1]

    def size(self):
        return len(self.items)

    def push(self, item):
        if self.size() >= self.stack_size:
            for i in range(self.size() - self.stack_size + 1):    # 压栈时，超过设置大小时，将最前面数据移除
                self.items.remove(self.items[0])
            # self.items.clear()    # 压栈时，超过缓冲区大小，直接清空
        self.items.append(item)