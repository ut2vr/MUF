#!/usr/bin/python3
# coding:utf-8
"""
Usage: map.py -d <date> -t <time> -i <interval> -b <band> -m <mode>"
Arguments:
 -d, --date       any datetime from 2018-04-15 to current datetime
 -t, --time       any time from 00:00 to 23:59
 -i, --interval   any value in minutes
 -b, --band       band 2m, 6m, 10m, all
 -m, --mode       mode cw, ft8, all
Flags:
 -h      help
"""
import folium
from folium import plugins
from folium.features import DivIcon
from folium import FeatureGroup, LayerControl
from folium.plugins import MousePosition
from folium.plugins import HeatMap
from folium.plugins import LocateControl
import branca.colormap as cm
import os
import webbrowser
import radio as r
import muf_base
import datetime
import getopt
import sys
import time
from math import sin, asin, cos, atan2, sqrt, radians, degrees


def WWMLocatorGreed(minlat, minlong, maxlat, maxlong, group):
    # WWM locator greed
    for parallels in range(min_lat, max_lat + 1, 10):
        folium.PolyLine([[parallels, min_lon], [parallels, max_lon]], weight=2, color='gray').add_to(group)
        if parallels == max_lat:
            break
        for lines in range(parallels + 1, parallels + 10, 1):
            folium.PolyLine([[lines, min_lon], [lines, max_lon]], weight=1, color='gray').add_to(group)
    for meridians in range(min_lon, max_lon + 1, 20):
        folium.PolyLine([[min_lat, meridians], [max_lat, meridians]], weight=2, color='gray').add_to(group)
        if meridians == max_lon:
            break
        for lines in range(meridians, meridians + 20, 2):
            folium.PolyLine([[min_lat, lines], [max_lat, lines]], weight=1, color='gray').add_to(group)

    # WWM locator big square
    for parallels in range(min_lat, max_lat, 10):
        for meridians in range(min_lon, max_lon, 20):
            lat = parallels + 7
            lon = meridians + 6
            square = r.locator(lat, lon)[:2]
            folium.map.Marker(
                [lat, lon],
                icon=DivIcon(
                    icon_size=(150, 34),
                    icon_anchor=(0, 0),
                    html='<div style="font-size: 20pt">' + square + '</div>',
                )
            ).add_to(group)

    return group


def MyQTH(location, call, Escircle, TropoCircle, group):

    # One hup Es propagation circle
    folium.Circle(
        radius=Escircle,
        location=QTH,
        popup='One hup Es circle',
        color='crimson',  # '#428bca'
        fill=True,
        weight=1,
        fill_color='#428bca'
    ).add_to(group)

    # Tropo propagation circle
    folium.Circle(
        radius=TropoCircle,
        location=QTH,
        popup='Tropo circle',
        color='#428bca',
        fill=True,
        weight=1,
        fill_color='#428bca'
    ).add_to(group)

    # Home location
    folium.CircleMarker(
        radius=2,
        location=QTH,
        popup=call,
        color='crimson',
        fill=True,
        fill_color='#428bca'
    ).add_to(group)

    return group


def MUF_map(muf_list, group):
    data = []
    # отображение MUF
    for key in muf_list.keys():
        coord = r.coordinate(key+'JJ')
        MUF = muf_list[key]
        point = [coord[0], coord[1], (MUF - 50.0) / 100.0]
        data.append(point)

    gradient_map = {0.19: 'blue', 0.33: 'green', 0.46: 'yellow', 0.66: 'pink', 1.0: 'red'}
    HeatMap(data, name=None, max_zoom=4, min_opacity=0.5, radius=28, blur=22, gradient=gradient_map,
            overlay=True, control=True, show=True).add_to(muf)
    return group


def QSOdraw(coordinates, DxCall1, DxCall2, group, col):

    folium.PolyLine(
        smooth_factor=1,
        locations=coordinates,
        color='gray',
        tooltip=DxCall1+' <--> '+DxCall2,
        weight=1
    ).add_to(group)

    folium.CircleMarker(
        radius=2,
        location=coordinates[0],
        popup=DxCall1,
        tooltip=DxCall1,
        color=col,
        fill=True,
        fill_color='#428bca'
    ).add_to(group)

    folium.CircleMarker(
        radius=2,
        location=coordinates[-1],
        popup=DxCall2,
        tooltip=DxCall2,
        color=col,
        fill=True,
        fill_color='#428bca'
    ).add_to(group)

    return group


def QSOreqv(stdate, interval, band, mode):
    res, conn = muf_base.base_connect(**db_config)
    curs = conn.cursor()

    if band == '2m':
        bquery = ' and Band=' + chr(34) + band + chr(34)
    elif band == '4m':
        bquery = ' and Band=' + chr(34) + band + chr(34)
    elif band == '6m':
        bquery = ' and Band=' + chr(34) + band + chr(34)
    elif band == '10m':
        bquery = ' and Band=' + chr(34) + band + chr(34)
    elif band == 'fm':
        bquery = ' and (Band="TV" or Band="OIRT" or Band="CCIRT" or Band="VOR" or Band="AVIA")'
    else:
        bquery = ""
    if mode == 'CW':
        mquery = 'and Mode=' + chr(34) + mode + chr(34)
    elif mode == 'FT8':
        mquery = 'and Mode=' + chr(34) + mode + chr(34)
    else:
        mquery = ""

    query = ("SELECT DxLoc1, DxLoc2, CentrLoc, DxCall1, DxCall2, MUF, QTF1, QRB1 FROM tblspot "
             "WHERE (DxDateTime > {0} "
             "AND DxDateTime < {1})".format(edatet, stdatet))
    query = query + bquery + mquery
    curs.execute(query)
    spots = curs.fetchall()
    curs.close()
    conn.close()

    return spots


def MUF_reqv(stdate, interval):
    res, conn = muf_base.base_connect(**db_config)
    curs = conn.cursor()
    query = ("SELECT CentrLoc, MUF FROM tblspot WHERE (DxDateTime > {0} AND DxDateTime < {1})".format(edatet, stdatet))
    curs.execute(query)
    MUFs = curs.fetchall()
    curs.close()
    conn.close()
    for MUF_point in MUFs:
        CentrLoc, MUF = MUF_point
        if MUF < 50.0:
            continue
        key = CentrLoc[:4]
        if key in muf_list:
            if muf_list.get(key) > MUF:
                continue
        muf_list[key] = MUF
    return muf_list


def InermediatePoint(loc1, loc2, dist):
    imp = []
    dlat1, dlon1 = r.coordinate(loc1)
    dlat2, dlon2 = r.coordinate(loc2)
    lat1 = radians(dlat1)
    lat2 = radians(dlat2)
    lon1 = radians(dlon1)
    lon2 = radians(dlon2)
    d = dist / 6378.137  # WGS84
    f = 0.0
    if dist > 5000:
        step = 0.01
    else:
        step = 0.05
    while f <= 1.0 + step:
        A = sin((1 - f) * d) / sin(d)
        B = sin(f * d) / sin(d)
        x = A * cos(lat1) * cos(lon1) + B * cos(lat2) * cos(lon2)
        y = A * cos(lat1) * sin(lon1) + B * cos(lat2) * sin(lon2)
        z = A * sin(lat1) + B * sin(lat2)
        p = [degrees(atan2(z, sqrt(pow(x, 2) + pow(y, 2)))), degrees(atan2(y, x))]
        imp.append(p)
        f += step
    return imp

def usage():

    print(sys.exit(__doc__))

# сделать свою иконку с прозрачным фоном. Можно указать точки привязки
# homeIcon = folium.features.CustomIcon('logo.png', icon_size=(50, 50))


if __name__ == '__main__':

    INI_FILENAME = 'SpotCollector.ini'
    db_config = muf_base.get_base_conf(INI_FILENAME)

    stdate = datetime.datetime.utcnow()

    interval = 180
    band = 'all'
    mode = 'all'
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:t:i:b:m:")
    except getopt.GetoptError:
        usage()
    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt in ("-d", "--date"):
            try:
                stdate = datetime.datetime.strptime(arg,"%Y-%m-%d")
            except ValueError:
                usage()
        elif opt in ("-t", "--time"):
            try:
                sttime = datetime.datetime.strptime(arg, "%H:%M")
                stdate = stdate.replace(hour=sttime.hour, minute=sttime.minute)
            except ValueError:
                usage()
        elif opt in ("-i", "--interval"):
            interval = int(arg)
        elif opt in ("-b", "--band"):
            band = arg
        elif opt in ("-m", "--mode"):
            mode = arg.upper()
    stdatet = chr(34) + str(stdate)[:19] + chr(34)
    edate = stdate - datetime.timedelta(minutes=interval)
    edatet = chr(34) + str(edate)[:19] + chr(34)

    # print(stdatet, edatet)
    # sys.exit()

    QTH = r.my_qth()
    my_map = folium.Map(location=QTH, zoom_start=4, max_zoom=4, min_zoom=2, zoom_control=False,
                        min_lat=-40, max_lat=70, min_lon=-100, max_lon=140, max_bounds=True)

    plugins.Fullscreen(
        position='topleft',
        title='Expand me',
        title_cancel='Exit me',
        force_separate_button=True
    ).add_to(my_map)

# Locate
    LocateControl(auto_start=True).add_to(my_map)

# Colormap
#     colormap = cm.linear.Reds_03.scale(50, 150).to_step(10)
    colormap = cm.LinearColormap(
        ['green', 'yellow', 'orange', 'red'],
        vmin=50, vmax=150
    )
    col = colormap.to_step(
                            n=6,
                            data=[50, 51, 52, 53, 54, 56, 58, 70, 90, 130],
                            method='quantiles',
                            round_method='int'
                            )
    colormap.caption = 'MUF in MHz.         {0} min. before {1} UTC'\
        .format(interval, stdatet[1:17], band, mode)
    my_map.add_child(colormap)
# Circle
#     my_qth = FeatureGroup(name='My QTH', show=False)
#     MyQTH(QTH, 'UT2VR', 2000000, 800000, my_qth).add_to(my_map)
# Greed
    loc_greed = FeatureGroup(name='WWM Locator Greed', show=False)
    min_lat = -40
    max_lat = 70
    min_lon = -100
    max_lon = 160
    WWMLocatorGreed(min_lat, min_lon, max_lat, max_lon, loc_greed).add_to(my_map)
# Terminator
    lin = FeatureGroup(name='Terminator', show=False)
    plugins.Terminator().add_to(lin)
    lin.add_to(my_map)

# QSO 6m
    qso_6m = FeatureGroup(name='QSO 6m')
    spots = QSOreqv(stdate, interval, '6m', 'All')
    # print('Num spots={0}'.format(len(spots)))

    for spot in spots:
        DxLoc1, DxLoc2, CentrLoc, DxCall1, DxCall2, MUF, QTF1, QRB1 = spot

        #   Intermediate points on a great circle

        coordinates = InermediatePoint(DxLoc1, DxLoc2, QRB1)
        QSOdraw(coordinates, DxCall1, DxCall2, qso_6m, 'blue').add_to(my_map)

    # plugins.LocateControl().add_to(my_map)

# QSO 4m
    qso_4m = FeatureGroup(name='QSO 4m', show=True)
    spots = QSOreqv(stdate, interval, '4m', 'All')
    for spot in spots:
        DxLoc1, DxLoc2, CentrLoc, DxCall1, DxCall2, MUF, QTF1, QRB1 = spot
        coordinates = InermediatePoint(DxLoc1, DxLoc2, QRB1)
        QSOdraw(coordinates, DxCall1, DxCall2, qso_4m, 'green').add_to(my_map)

# FM
    fm = FeatureGroup(name='FM', show=True)
    spots = QSOreqv(stdate, interval, 'fm', 'All')
    for spot in spots:
        DxLoc1, DxLoc2, CentrLoc, DxCall1, DxCall2, MUF, QTF1, QRB1 = spot
        coordinates = InermediatePoint(DxLoc1, DxLoc2, QRB1)
        QSOdraw(coordinates, DxCall1, DxCall2, fm, 'yellow').add_to(my_map)

# QSO 2m
    qso_2m = FeatureGroup(name='QSO 2m', show=True)
    spots = QSOreqv(stdate, interval, '2m', 'All')
    for spot in spots:
        DxLoc1, DxLoc2, CentrLoc, DxCall1, DxCall2, MUF, QTF1, QRB1 = spot
        coordinates = InermediatePoint(DxLoc1, DxLoc2, QRB1)
        QSOdraw(coordinates, DxCall1, DxCall2, qso_2m, 'crimson').add_to(my_map)

# MUF
    muf_list = dict()
    coordinates = []
    muf = FeatureGroup(name='MUF', show=True)
    muf_list = MUF_reqv(stdate, interval)
    MUF_map(muf_list, muf).add_to(my_map)

# Position
    formatter = "function(num) {return L.Util.formatNum(num, 3) + 'º ';};"

    MousePosition(
        position='topright',
        separator=' | ',
        empty_string='NaN',
        lng_first=True,
        num_digits=20,
        prefix='Coordinates:',
        lat_formatter=formatter,
        lng_formatter=formatter
    ).add_to(my_map)

    LayerControl().add_to(my_map)
    file_path = os.path.dirname(os.path.abspath(__file__)) + '/es.html'

    my_map.save(file_path)
    url = 'file://' + file_path

    # webbrowser.open(url)

