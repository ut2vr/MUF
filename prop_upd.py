#!/usr/bin/python3
# coding:utf-8
"""
Ищет все записи с неопределенным типом распространения.
На основе анализа комментария спота пытается определить тип.
Записи обновляются в tblallspot
"""
#   TODO: вычистить FT8 тропо споты
import mysql.connector
from mysql.connector import Error
import sys
import muf_base

muf_base.get_prop_list()

try:
    conn = mysql.connector.connect(host='192.168.1.16', user='mufuser', password='mufpasswd', database='MUF')
except Error as e:
    sys.exit()

try:
    conn1 = mysql.connector.connect(host='192.168.1.16', user='mufuser', password='mufpasswd', database='MUF')
except Error as e:
    sys.exit()
curs1 = conn1.cursor()
curs = conn.cursor()
curs.execute("SELECT * FROM tblallspot WHERE prop = 'UNKNOWN'")
rows = curs.fetchall()
query = """update tblallspot SET prop = %s where (date = %s) AND (spotter = %s) """
n = 0
for row in rows:
    date, spotter, loc1, dx, loc2, freq, comment, prop, mode, qrb = row
    prop_new = muf_base.find_par(comment)[0]
    if prop_new != "UNKNOWN":
        if not (prop_new == "RAIN" and freq < 5000):
            data = (prop_new, date, spotter)
            curs1.execute(query, data)
            print(date, prop_new, comment)
            n += 1
print(n, 'records modified')
conn1.commit()
curs.close()
conn.close()
curs1.close()
conn1.close()


