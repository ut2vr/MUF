#!/usr/bin/python3
# coding:utf-8

import sys
import subprocess
from PyQt5 import QtWidgets, QtGui

from MUF_map import Ui_MainWindow
import datetime

'''
Form Qt5
preparation of parameters for map.py
'''

stdate = datetime.datetime.utcnow()
intrv = 15
band = '6m'
mode = 'FT8'

class mywindow(QtWidgets.QMainWindow):

    def __init__(self):

        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.scr_time.valueChanged[int].connect(self.on_time_change)
        self.ui.cb_interval.currentIndexChanged[int].connect(self.on_interval_change)
        self.ui.pushButton.clicked.connect(self.on_show)
        self.ui.pb_now.clicked.connect(self.on_now)
        self.ui.cb_band.currentIndexChanged[int].connect(self.on_band_change)
        self.ui.cb_mode.currentIndexChanged[int].connect(self.on_mode_change)
        self.ui.dateTimeEdit.setDateTime(stdate)
        self.pos_to_time()

    def on_show(self):

        # map.py - d < date > -i < interval > -b < band > -m < mode >
        global intrv, band, mode
        dt = self.ui.dateTimeEdit.dateTime().toPyDateTime()
        args = ['./map.py', '-d', str(dt)[:10], '-t', str(dt)[11:16], '-i', str(intrv), '-b', band, '-m', mode]

        stdate = datetime.datetime.utcnow()
        subprocess.call(args)
        self.statusBar().showMessage(str(datetime.datetime.utcnow() - stdate))

    def pos_to_time(self):

        # установка движка по времени
        t = self.ui.dateTimeEdit.time()
        # TODO: изменить конструкцию
        h = int(t.toString('hh'))
        m = int(t.toString('mm'))
        pos = h * 4 + m // 15 + 1
        self.ui.scr_time.setValue(pos)
        self.on_time_change(pos)

    def on_time_change(self, pos):
        # pos 0--95

        h = pos // 4
        m = pos % 4
        m = m * 15

        dt = self.ui.dateTimeEdit.dateTime().toPyDateTime()
        dt = dt.replace(hour=h, minute=m, second=0)
        self.ui.dateTimeEdit.setDateTime(dt)

    def on_now(self):
        self.ui.dateTimeEdit.setDateTime(datetime.datetime.utcnow())

    def on_interval_change(self, ind):
        # время отсчитывается в 15 минутных интервалах
        global intrv
        self.ui.scr_time.setEnabled(True)

        case = self.ui.cb_interval.currentIndex()
        if case == 0:  # day
            self.ui.scr_time.setEnabled(False)
            intrv = 60 * 24
        elif case == 1:  # 6 hour
            self.ui.scr_time.setSingleStep(24)
            self.ui.scr_time.setPageStep(48)
            intrv = 60 * 6
        elif case == 2:  # 3 hour
            self.ui.scr_time.setSingleStep(12)
            self.ui.scr_time.setPageStep(24)
            intrv = 60 * 3
        elif case == 3:  # 1 hour
            self.ui.scr_time.setSingleStep(4)
            self.ui.scr_time.setPageStep(8)
            intrv = 60
        elif case == 4:  # 30 min
            self.ui.scr_time.setSingleStep(2)
            self.ui.scr_time.setPageStep(4)
            intrv = 30
        elif case == 5:
            self.ui.scr_time.setSingleStep(1)
            self.ui.scr_time.setPageStep(4)
            intrv = 15

            # выравнять время по границе интервала

    def on_band_change(self, ind):
        global band

        self.ui.cb_mode.setEnabled(True)
        case = self.ui.cb_band.currentIndex()
        if case == 0:
            band = '10m'
        if case == 1:
            band = '6m'
        if case == 2:
            band = '4m'
        if case == 3:
            band = '2m'
        if case == 4:
            band = 'fm'
            self.ui.cb_mode.setCurrentIndex(2)
            self.ui.cb_mode.setEnabled(False)

    def on_mode_change(self, ind):
        global mode

        case = self.ui.cb_mode.currentIndex()
        if case == 0:
            mode = 'CW'
        if case == 1:
            mode = 'FT8'
        if case == 2:
            mode = 'All'


app = QtWidgets.QApplication([])
application = mywindow()
application.show()

sys.exit(app.exec())
