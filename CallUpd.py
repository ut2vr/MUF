#!/usr/bin/python3
# coding:utf-8

"""
https://www.mmmonvhf.de/dl.php?dl=call3.txt
Search in current directory file "call3.txt".
Read callsign and WWM locator.
Update tbldxstation in base MUF
Four symbol WWM locator ignore

iconv -f iso-8859-1 -t UTF-8 -o call.txt call3.txt
"""

import csv
import sys
import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import logging
import muf_base

logging.basicConfig(format=u'%(filename)-17s [LINE:%(lineno)3d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    filename='UpdInfo.log', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

INI_FILENAME = 'SpotCollector.ini'

db_config = muf_base.get_base_conf(INI_FILENAME)

localname = 'call3.txt'
clist = [[[], []]]
toins = [[[], []]]

logging.info('Start update call list')

if not os.path.isfile(localname):
    print('File {} not found'.format(localname))
    sys.exit()

try:
    conn = mysql.connector.connect(**db_config)
except Error as e:
    logging.error(e)
    sys.exit()

curs = conn.cursor()

# Удаление из базы записей четырехсивольными локаторами
# query = 'delete FROM tbldxstation where length(dxlocatorid) < 6;'

date = datetime.utcnow()
rec = list([[], [], []])

with open(localname, "rb") as F:
    text = F.read()
    try:
        text = text.decode("iso-8859-1")
        text = text.encode("utf-8")
        with open(localname, "wb") as f:
            f.write(text)
    except:
        logging.info('Decode / encode error')

with open(localname) as csvfile:
    users = csv.reader(csvfile, delimiter=',', quotechar='"')
    for user in users:
        try:
            call = user[0]
            loc = user[1]
        except IndexError:
            continue
        if len(loc) != 6:
            continue
        # call = call.decode()
        # loc = loc.decode()
        rec = call, loc, date
        try:
            query = "select dxcallsign, dxlocatorid from tbldxstation where dxcallsign=" + chr(39)+call+chr(39)+';'
            curs.execute(query)
            curs.fetchall()
            if not curs.rowcount == 1:
                logging.info("Record append {0} {1}".format(call, loc))
                query = 'INSERT INTO tbldxstation (dxcallsign, dxlocatorid, DxDate) values (%s, %s, %s);'
                curs.execute(query, rec)
                # break
        except Error as e:
            logging.error(e)
        conn.commit()
logging.info('Update call list complit')
curs.close()
conn.close()
os.remove(localname)
