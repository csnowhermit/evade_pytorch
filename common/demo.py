from common.config import conn, cursor
from common.dbUtil import create_detail_info_table

table_name = "details_127_0_0_1"

ids = "ids"
# print(create_detail_info_table(table_name))

# sql = '''
#     INSERT INTO %s(name, age) VALUES ('%s', %d)
# '''.format(table_name)


data = [("Alex", 18), ("Egon", 20), ("Yuan", 21)]
try:
    # 批量执行多条插入SQL语句
    # cursor.executemany(sql, data)
    for dd in data:
        print(dd[0], type(dd[0]))
        print(dd[1], type(dd[1]))
        sql = "insert into %s" % table_name
        # sql = sql + "(name, age) VALUES ('%s', %d)" % ()
        sql = sql + '''
            (ids, name, age) VALUES ('%s', '%s', %d)
        ''' % (ids, dd[0], dd[1])

        cursor.execute(sql)
    # 提交事务
    conn.commit()
    print("conn.commit()!")

except Exception as e:
    # 有异常，回滚事务
    print(e)
    conn.rollback()
    print("conn.rollback()!!")