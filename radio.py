#!/usr/bin/python3
# coding:utf-8

"""
 Amateur radio program library
"""


from math import sin, cos, tan, atan2, atan, sqrt, trunc, radians, degrees, pi
import re
from datetime import datetime
from datetime import date

def my_qth():
    """
    :return: geographical coordinate of my QTH
    home: 49.05279920 33.22420532 161,4m MSL
    """
    return 49.0837, 33.2598


def coordinate(loc):
    """
    Calculate geographical coordinate from WWM locator
    Locator in upper case
    TODO: добавить 8 символьную нотацию
    """
    long = -180 + (ord(loc[0]) - 65) * 20 + int(loc[2]) * 2
    long += ((ord(loc[4]) - 65) * 5 + 2.5) / 60
    lat = -90 + (ord(loc[1]) - 65) * 10 + int(loc[3])
    lat += ((ord(loc[5]) - 65) * 2.5 + 1.25) / 60

    return lat, long


def locator(lat, long):
    """
    Determine WWM locator from geographical coordinates
    TODO: добавить 8 символьную нотацию
    """
    lo = long + 180
    la = lat + 90
    loc = chr(65 + trunc(lo / 20))  # 1 letter
    loc += chr(65 + trunc(la / 10))  # 2 letter
    loc += chr((48 + trunc((lo - (ord(loc[0]) - 65) * 20) / 2)))  # 1 number
    loc += chr(48 + trunc((la - (ord(loc[1]) - 65) * 10)))  # 2 number
    loc += chr(65 + trunc((lo - (ord(loc[0]) - 65) * 20 - (ord(loc[2]) - 48) * 2) / (5.0 / 60.0)))  # 3 letter
    loc += chr(65 + trunc((la - (ord(loc[1]) - 65) * 10 - (ord(loc[3]) - 48)) / (2.5 / 60.0)))  # 4 letter

    return loc


def distance(loc1, loc2):
    """
    calculate great circle distance in kilometer form locator1 to locator2
    """
    r = 6378.137  # WGS84
    lat1, long1 = coordinate(loc1)
    lat2, long2 = coordinate(loc2)
    d_lat = radians(lat2) - radians(lat1)
    d_long = radians(long2) - radians(long1)
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)
    a = sin(d_lat / 2) * sin(d_lat / 2) + cos(r_lat1) * cos(r_lat2) * sin(d_long / 2) * sin(d_long / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = r * c

    return d


def heading(loc1, loc2):
    """
    calculate heading in decimal degrees from locator1 to locator2
    """
    lat1, long1 = coordinate(loc1)
    lat2, long2 = coordinate(loc2)
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)
    d_lon = radians(long2 - long1)
    b = (atan2(sin(d_lon) * cos(r_lat2), cos(r_lat1) * sin(r_lat2) - sin(r_lat1) *
               cos(r_lat2) * cos(d_lon)))
    bd = degrees(b)
    br, bn = divmod(bd + 360, 360)

    return bn


def point(loc1, dist, azimuth):
    """
    calculate WWM locator of the point locator1 in azimuth at a distance
    """
    s_lat, s_long = coordinate(loc1)
    s1 = sin(radians(s_lat))
    sd = sin(radians(dist / 111.195))
    sa = sin(radians(azimuth))
    c1 = cos(radians(s_lat))
    ca = cos(radians(azimuth))
    cd = cos(radians(dist / 111.195))
    sin_fi2 = s1 * cd + c1 * sd * ca
    lat2 = degrees(atan2(sin_fi2, sqrt(1 - pow(sin_fi2, 2))))
    long2 = s_long + degrees(atan2(sd * sa, c1 * cd - s1 * sd * ca))
    return locator(lat2, long2)


def check_loc(loc):
    """
    check 6 symbol WWM locator
    locator in upper case
    TODO: добавить 8 символьную нотацию
    """
    loc = loc.upper()
    big_sq_let = frozenset('ABCDEFGHIJKLMNOPQR')
    sm_sq_let = frozenset('ABCDEFGHIJKLMNOPQRSTUVWX')
    dig = frozenset('0123456789')
    res = False
    if len(loc) == 6:
        if loc[0] in big_sq_let:
            if loc[1] in big_sq_let:
                if loc[2] in dig:
                    if loc[3] in dig:
                        if loc[4] in sm_sq_let:
                            if loc[5] in sm_sq_let:
                                res = True

    return res


band_list = [[28.000, 29.700, '10m'], [50.000, 54.000, '6m'], [49.000, 65.000, 'TV'], [70.000, 70.700, '4m'],
             [65.900, 74.000, 'OIRT'], [87.500, 108.000, 'CCIRT'], [108.000, 117.950, 'VOR'],
             [118.000, 136.000, 'AVIA'], [140.000, 148.000, '2m'], [220.000, 222.000, '1m'], [430.000, 440.000, '70cm'],
             [1240.000, 1325.000, '23cm'], [5650.000, 5850.000, '6cm'], [10000.000, 10500.000, '3cm'],
             ]


def det_band(freq):
    """
    Determine band name by frequency
    :param freq:
    :return: band
    """
    global band_list

    band = 'UNKNOWN'
    for s in band_list:
        if freq >= s[0]:
            if freq <= s[1]:
                band = s[2]
                break

    return band


def spot_parse(spot):
    """
    Parse spot from DxCluster
    :param spot:
    :return: result, (dt, spotter, dx, fr, comment)
    """
    callsign_pattern = "([a-z|0-9|/]+)"
    frequency_pattern = "([0-9|.]+)"
    spot_pattern = re.compile(
        "^DX de " + callsign_pattern + ":\s+" + frequency_pattern + "\s+" + callsign_pattern + "\s+(.*)\s+(\d{4}Z)",
        re.IGNORECASE)
    match = spot_pattern.match(spot)
    # If there is a match, sort matches into variables
    if match:
        spotter = match.group(1)
        fr = round((float(match.group(2)) / 1000), 3)
        dx = match.group(3)
        comment = match.group(4).strip()
        tim = match.group(5)[0:4]
        tim = tim[:2] + ':' + tim[2:]
        dat = date.isoformat(datetime.utcnow()) + ' ' + tim + ':00'
        dt = datetime.strptime(dat, '%Y-%m-%d %H:%M:%S')
        return True, (dt, spotter, dx, fr, comment)
    else:
        return False, (None, None, None, None, None)


def _muf_calc(qrb, freq):
    """
    Calculate MUF ,Elevation & Critical frequency
    """
    masl = 0.150
    layer = 110
    equator_len = 40000
    eart_rad = equator_len / 2 / pi + masl
    max_muf_factor = 5.44886093504785

    centr_ang = qrb / equator_len * 2 * pi
    hor = eart_rad * sin(centr_ang / 2)
    vert = hor / tan((pi - centr_ang / 2) / 2)
    elev = degrees(atan((vert + layer) / hor) - centr_ang / 2)
    muf_angle = atan(hor / (vert + layer))
    muf_factor = 1 / cos(muf_angle)
    muf = max_muf_factor / muf_factor * freq
    crit_freq = muf / max_muf_factor

    return muf, elev, crit_freq


def sp_e_reflect(try_from, spot_prep):
    """
    Input: [date, spotter, loc1, dx, loc2, freq, comment, prop, mode, qrb, band]
    *** loc1 != loc2 ***
    calculating of all Es reflection parameters
    """
    _, _, loc1, _, loc2, freq, _, _, _, qrb, _ = spot_prep

    res = False
    if (loc1 == loc2) or (qrb == 0):
        return res

    qrb1 = qrb
    qtf1 = heading(loc1, loc2)
    centr_loc = point(loc1, qrb1 / 2, qtf1)
    muf, elev1, crit_freq = _muf_calc(qrb1, freq)
    qtf2 = heading(try_from, centr_loc)
    qrb_to_mp = distance(try_from, centr_loc)
    qrb2 = qrb_to_mp * 2
    try_to = point(try_from, qrb2, qtf2)
    fot, elev2, ang = _muf_calc(qrb2, freq)
    res = True

    return [res, round(qtf1, 1), round(elev1, 1), round(qrb1, 1), centr_loc, round(crit_freq, 1),
            round(muf, 1), try_from, try_to, round(qtf2, 1), round(elev2, 1), round(qrb2, 1),
            round(fot, 1), round(qrb_to_mp, 1)]


def _test_geo(test_set):

    lat1, long1, lat2, long2 = test_set[0]

    loc1 = locator(lat1, long1)
    loc2 = locator(lat2, long2)
    dist = round(distance(loc1, loc2), 1)
    az = round(heading(loc1, loc2), 1)
    cen_loc = point(loc1, dist/2, az)
    res = [loc1, loc2, dist, az, cen_loc]
    res1 = test_set[1]
    try:
        assert res == res1
    except AssertionError:
        print('NOT PASS')
    else:
        print('PASS', end=' ')


if __name__ == '__main__':
    print('Test geodesics function')

    test_sets = [
        [[77.1539, -139.398, -77.1804, -139.55], ['CQ07HD', 'CB02FT', 17180.3, 180.1, 'CI09GV']],
        [[77.1539, 120.398, 77.1804, 129.55], ['PQ07ED', 'PQ47SE', 226.5, 84.4, 'PQ27LE']],
        [[77.1539, -120.398, 77.1804, 129.55], ['CQ97TD', 'PQ47SE', 2335.2, 324.4, 'AR22HN']]
                ]
    for test_set in test_sets:
        _test_geo(test_set)

#	Точка 1	                Точка 2	        Расстояние	Угол
# 1	77.1539/-139.398	-77.1804/-139.55	17166029	180.077867811
# 2	77.1539/120.398	    77.1804/129.55	    225883	    84.7925159033
# 3	77.1539/-120.398	77.1804/129.55	    2332669	    324.384112704
    print('\n')
    res, spot = spot_parse("DX de WW1L:      50313.0  EA6CA        FT8 -19 dB 1106hz 1st          1951Z FN54")
    print(spot)
# DX de XE3N:      50313.0  TO11A        EL60LP<>FK96DD FT8 tnx QSO 73  1948Z
# DX de WW1L:      50313.0  EA6CA        FT8 -19 dB 1106hz 1st          1951Z FN54
