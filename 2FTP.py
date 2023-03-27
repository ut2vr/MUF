#!/usr/bin/python3
# coding:utf-8

import datetime
import subprocess
import os
import ftplib

if __name__ == '__main__':
    stdate = datetime.datetime.utcnow()
    file_path = os.path.dirname(os.path.abspath(__file__))
    args = [file_path + '/map.py', '-d', str(stdate)[:10], '-t', str(stdate)[11:16], '-i', '30', '-b', 'All', '-m', 'All']

    subprocess.call(args)

    try:
        ftp = ftplib.FTP('vhfdx.ftp.tools', 'vhfdx_ut2vr ', 'C2operation')
    except ftplib.all_errors as e:
        print('FTP error:', e)
    else:
        file_name = 'es.html'
        with open(file_path + '/es.html', 'rb') as fobj:
            store_com = "STOR {}".format(file_name)
            resp = ftp.storbinary(store_com, fobj)
            print(resp)
            ftp.quit()
