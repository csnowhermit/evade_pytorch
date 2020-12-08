import time

items = []

items.append((101, "A"))
items.append((102, "B"))
items.append((103, "C"))
items.append((104, "D"))
items.append((105, "E"))

index = [i for i in range(len(items)) if items[i][0]==103][0]
print(index)

tmp = items[1:3]
print(tmp)

del items[0]

print(items)
print(tmp)