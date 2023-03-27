#!/usr/bin/python3
# coding:utf-8

"""
Reading user list of the LoTW system
and create  new tbllotw in database MUF
"""
import csv
import os
import sys
import urllib.request
import mysql.connector
from mysql.connector import Error
import logging
import muf_base


logging.basicConfig(format=u'%(filename)-17s [LINE:%(lineno)3d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    filename='UpdInfo.log', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

INI_FILENAME = 'SpotCollector.ini'

db_config = muf_base.get_base_conf(INI_FILENAME)

localname = 'lotw_list.csv'
sourcename = 'https://lotw.arrl.org/lotw-user-activity.csv'
try:
    urllib.request.urlretrieve(sourcename, localname)
except Error:
    logging.error("Connection to lotw.arrl.org is impossible")
    sys.exit()
logging.info('Start updating LoTW table')

try:
    conn = mysql.connector.connect(**db_config)
except Error as e:
    logging.error(e)
    sys.exit()

curs = conn.cursor()
query = "DROP TABLE IF EXISTS tbllotw;"
curs.execute(query)

query = "CREATE TABLE tbllotw (LoTW_Call varchar(20) DEFAULT NULL, " \
        "LoTW_date datetime NOT NULL DEFAULT '0000-00-00 00:00:00');"
curs.execute(query)

query = 'INSERT INTO tbllotw (LoTW_Call, LoTW_date) values (%s,%s);'

logging.info('Update tbllotw')

with open(localname) as csvfile:
    users = csv.reader(csvfile, delimiter=',', quotechar='"')
    for user in users:
        rec = (user[0], user[1] + ' ' + user[2])
        try:
            curs.execute(query, rec)
        except Error as e:
            logging.error(e)
    conn.commit()
logging.info('Add %s records', curs.rowcount)
curs.close()
conn.close()
os.remove(localname)
