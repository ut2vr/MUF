#!/usr/bin/python3
# coding:utf-8

# Get FM spots file http://www.fmlist.org/livemuf.txt
# Parse as csv
# Write in tblspot

import mysql.connector
import radio as r
import csv
import os
import urllib.request
from datetime import datetime
from datetime import date
import logging
import muf_base


logging.basicConfig(format=u'%(filename)-17s [LINE:%(lineno)3d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    filename='UpdInfo.log', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

INI_FILENAME = 'SpotCollector.ini'

db_config = muf_base.get_base_conf(INI_FILENAME)

localname = 'FM_list '  # + '2019-05-03'   #date.isoformat(datetime.utcnow())
logging.info('Start ' + localname + ' reading')
remoteaddr = 'http://%s%s' % ('www.fmlist.org', '/livemuf.txt')  # can name a CGI script too

try:
    urllib.request.urlretrieve(remoteaddr, localname)  # can be file or script
except OSError as err:
    logging.error('www.fmlist.org %s', err)
try:
    remotedata = open(localname, encoding='cp1251', errors='replace').readlines()  # saved to local file
except OSError as err:
    logging.error(localname + ' %s', err)

conn = mysql.connector.connect(**db_config)
curs = conn.cursor()
curs.execute('select DxDateTime from tblspot where DxCall1="FMsp"')

spots = curs.fetchall()
lastdate = spots[curs.rowcount-1][0]
records = 0

query = ("insert into tblspot "
         "(DxDateTime, DxCall1, DxLoc1, DxCall2, DxLoc2, Freq, SpotInfo, QTF1, Elev1, QRB1,"
         "CentrLoc, CritFreq, MUF, TryFrom, TryTo, QTF2, Elev2, QRB2, FOT, Qrb_To_Midpoint, Band)"
         "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

with open(localname, encoding='cp1251') as csvfile: #, errors='replace'
    spots = csv.reader(csvfile, delimiter='|', quotechar='"')
    for spot in spots:
        DxDateTime, DxCall1, DxLoc1, DxCall2, DxLoc2, Freq, _ = spot
        try:
            dt = datetime.strptime(DxDateTime, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            logging.error('Bad date %s', DxDateTime)
            continue
        DxDateTime = dt
        try:
            fr = float(Freq) / 1000
        except ValueError as err:
            logging.error('Bad freq %s', Freq)
            continue
        if DxDateTime > lastdate:
            if DxLoc1 == DxLoc2:
                continue
            if r.check_loc(DxLoc1) is False:
                continue
            if r.check_loc(DxLoc2) is False:
                continue
            qrb = r.distance(DxLoc1, DxLoc2)
            pars_spot = [DxDateTime, 'FMsp', DxLoc1, 'FMdx', DxLoc2, fr, 'www.fmlist.org/livemuf.txt', 'ES', 'FM', qrb, 'FMrad']
            band = r.det_band(fr)
            if band == '4m':
                band = 'OIRT'
            res, qtf1, Elev1, QRB1, CentreLoc, CritFreq, MUF, TryFrom, \
            TryTo, Qtf2, Elev2, QRB2, FOT, Qrb_To_Midpoint = r.sp_e_reflect('KN69PC', pars_spot)

            if res is True:
                muf_spot = [DxDateTime, 'FMsp', DxLoc1, 'FMdx', DxLoc2, fr, 'www.fmlist.org', qtf1, Elev1, QRB1, CentreLoc, CritFreq,
                            MUF, TryFrom, TryTo, Qtf2, Elev2, QRB2, FOT, Qrb_To_Midpoint, band]
            curs.execute(query, muf_spot)
            records += 1
        else:
            continue
curs.close()
conn.close()
os.remove(localname)
logging.info('Stored %s records', records)
