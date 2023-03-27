#!/usr/bin/python3
# coding:utf-8

import radio as r
import mysql.connector
from mysql.connector import Error
import sys
import re
from configparser import ConfigParser


mode_list = [['CW'], ['FT8', 28.074, 50.313, 50.314, 50.315, 50.323, 50.324, 50.325, 70.154, 70.155, 70.156, 144.174,
                      432.174], ['JT65', 50.176, 144.176, 432.176],
             ['MSK144', 50.260, 50.280, 144.360], ['FSK441', 144.370], ['JT65B'], ['JT6M'],
             ['JTMS'], ['PI4'], ['OPERA'], ['JT65A'], ['JT65C'], ['PHONE', 145.500], ['SSB'], ['RTTY'], ['FT4', 50.318]]
# TODO: перенести mode_list в базу данных

prop_list = []  # propagation list


def find_par(comment):
    """
    анализ comment с использованием шаблонов вида lo56ex<TR>lo48to lo56<TR>lo48
    RETURN: prop, loc1, loc2
    """
    global prop_list

    prop = 'UNKNOWN'
    loc1 = 'UNKNOWN'
    loc2 = 'UNKNOWN'
    pr = ''
    grid_pattern = "[a-r]{2}\d{2}([a-x]{2})?"
    grid6_pattern = "[A-R]{2}\d{2}[A-X]{2}"
    propagation_pattern = "\W*\w+\W*"
    rs_pattern = "[3-5][1-9]([AFS])\s"  # 55A 55S 55F
    pattern = re.compile(grid_pattern + propagation_pattern + grid_pattern, re.IGNORECASE)  # JN66OA<TR>JN12LL
    rs_patt = re.compile(rs_pattern, re.IGNORECASE)
    match = pattern.search(comment)
    if match:   # есть 4 или 6 симв. локаторы
        s = match.group(0).upper()
        if re.search(grid6_pattern, s):
            loc1 = s[0:6]     # первый 6 симв.
            s = s[6:]
            if re.search(grid6_pattern, s):
                loc2 = s[-6:]     # второй 6 симв.
                pr = s[:len(s) - 6]
            else:
                loc2 = s[-4:]     # второй 4 симв.
                pr = s[:len(s) - 4]
        else:
            pr = s[4:match.end() - match.start() - 4]   # оба локатора 4 симв.
    else:
        match1 = rs_patt.search(comment)    # find RS
        if not match1:
            for i in range(len(prop_list)):  # find from prop_list
                if _find_substr(comment, prop_list[i][1]):
                    prop = prop_list[i][0]
                    break
            return prop, loc1.upper(), loc2.upper()
        else:
            pr = match1.group(0)[:3].upper()

    for i in range(len(prop_list)):
        if pr == prop_list[i][1]:
            prop = prop_list[i][0]

    return prop, loc1.upper(), loc2.upper()


def test_find_par(test_set):
    comment, result = test_set
    res = find_par(comment)[0]
    try:
        assert res == result
    except AssertionError:
        print('comment = {0} result = {1} expected {2}\n'.format(comment, res, result))
    else:
        print('PASS', end=' ')


def _find_substr(com, s):
    """
    Ищет слово в строке
    """
    ind = com.find(s)
    if ind == -1:
        return False
    if com.startswith(s):  # поискать в начале
        if com == s:
            return True
        if com[ind + len(s)] == ' ':
            return True
        else:  # в начале было, но не ораничено пробелом
            ind = com.find(s, len(s))  # искать возможное следующее вхождение
    if com.endswith(s):  # поискать в конце
        if com[len(com) - len(s) - 1] == ' ':
            return True
    if 0 < ind < (len(com) - len(s)):  # поискать в средине, если индекс в допустимых границах
        if com[ind + len(s)] == ' ' and com[ind - 1] == ' ':
            return True  # вхождение найдено и ораничено пробелами

    # if re.search(s, com) is not None:
    #     return True     # unterminated subpattern at position 0.  s = '(ES:'

    return False


def find_mode(comment, freq):
    """
    Trying to determine the mode from spot comment and frequency.
    """
    global mode_list
    freq = round(freq, 3)
    com = comment.upper()
    mode = 'UNKNOWN'

    for i in range(len(mode_list)):
        if _find_substr(com, mode_list[i][0]):
            mode = mode_list[i][0]
            break

    if mode == 'UNKNOWN':  # выбор из mode_list элемента, соответствующего freq
        for i in range(len(mode_list)):
            if freq in mode_list[i]:
                mode = mode_list[i][0]

    if mode == 'UNKNOWN':  # поиск рапорта RST
        ind = com.find('5')
        while ind > -1:
            if ind < len(com) - 2:  # проверка индекса на допустимость
                rst = com[ind:ind+3]
                if rst.isdigit():
                    if _find_substr(com, rst):
                        mode = 'CW'
                        break
                ind += 1        # поискать дальше
            else:
                break

    return mode


def test_find_mode(test_set):
    comment, freq, result = test_set

    res = find_mode(comment, freq)
    try:
        assert res == result
    except AssertionError:
        print('\r\nfreq = {0} result = {1} expected {3}\ncomment = {2}'.format(freq, res, comment, result))
    else:
        print('PASS', end=' ')


def _recogn_prop(prop, qrb, mode, band):
    """
    Recognize propagation by mode, band, distance etc.
    если не определено другим способом
    :return: prop
    """

    if qrb < 900:  # любой модой на VHF+ диапазонах это тропо
        prop = 'TROPO'

    if band == '6m' or band == '4m' or band == '2m':
        if mode == 'FT8' or mode == 'CW' or mode == "PI4" or mode == "SSB":
            if qrb > 1200:                                     # летом в сезон спорадиков
                prop = 'ES'
            else:
                prop = 'TROPO'
        if mode == 'MSK144' or mode == 'FSK441' or mode == 'JTMS':
            if qrb > 900:
                if qrb < 2100:
                    prop = 'MS'
        if mode == 'JT65B' or mode == 'JT65':
            if qrb > 900:
                prop = 'EME'

    if band == '10m':       # тут можно уточнять для 10m & microWave band
        if qrb > 8000:
            prop = 'F2'
        if qrb > 600:
            if qrb < 1200:
                prop = 'ES'

    return prop


def get_base_conf(ini_file):
    parser = ConfigParser()
    parser.read(ini_file)

    db_config = {}
    items = parser.items('MySQL')
    for item in items:
        db_config[item[0]] = item[1]
    return db_config


def base_connect(db_conf):
    """
    Connect to base
    :return: res, conn
    """

    res = False
    conn = None
    try:
        conn = mysql.connector.connect(**db_conf)
        if conn.is_connected():
            res = True
    except Error:
        res = False

    return res, conn


def get_prop_list():
    """
    Initialise list of propagation type
    """
    global prop_list

    res, conn = base_connect(**db_config)
    curs = None
    if res is True:
        try:
            curs = conn.cursor()
            curs.execute('select * from tblprop')
            prop_list = curs.fetchall()
        except Error:
            res = False
        finally:
            curs.close()
            conn.close()
    return res


def find_loc_base(call):
    """
    find QRA locator for call in the table tbldxstation
    """

    loc = 'UNKNOWN'
    res, conn = base_connect(**db_config)
    if res is True:
        curs = conn.cursor()
        try:
            curs.execute('select dxlocatorId from tbldxstation where dxcallsign=' + chr(39) + call + chr(39))
        except Error:
            loc = 'UNKNOWN'
        else:
            loc = curs.fetchone()
        finally:
            curs.close()
            conn.close()
        if loc is None:
            loc = 'UNKNOWN'
        else:
            loc = loc[0]

    return loc


def spot_processed(raw_spot):
    """
    Парсинг сырого спота и
    проверка содержимого полей
    на допустимость значений

    :param raw_spot: list [dt, spotter, dx, freq, comment]
    :return: result: bool, pars_spot: list, reson: str
    pars_spot = date, spotter, loc1, dx, loc2, freq, comment, prop, mode, qrb, band
    """

    date, spotter, dx, freq, comment = raw_spot
    prop, loc1, loc2 = find_par(comment)  # по шаблону

    # поискать локаторы в базе, если есть - заменить
    loc = find_loc_base(spotter)
    if loc != 'UNKNOWN':
        loc1 = loc
    loc = find_loc_base(dx)
    if loc != 'UNKNOWN':
        loc2 = loc

    mode = find_mode(comment, freq)  # из спота или по частоте
    band = r.det_band(freq)

    if not r.check_loc(loc1):
        loc1 = 'UNKNOWN'
    if not r.check_loc(loc2):
        loc2 = 'UNKNOWN'

    if loc1 != 'UNKNOWN' and loc2 != 'UNKNOWN':
        qrb = r.distance(loc1, loc2)
    else:
        qrb = 0

    if prop == 'UNKNOWN':
        prop = _recogn_prop(prop, qrb, mode, band)  # уточнение по дистанции, диапазону

    pars_spot = [date, spotter, loc1, dx, loc2, freq, comment, prop, mode, qrb, band]

    result = True
    reson = ''
    if freq == 0:
        return False, pars_spot, 'Frequency not recognized'
    if spotter == dx:
        return False, pars_spot, 'Self spotting'
    if loc1 == 'UNKNOWN':
        result = False
        reson = 'Spotter WWM locator is UNKNOWN. '
    if loc2 == 'UNKNOWN':
        result = False
        reson += 'Dx WWM locator is UNKNOWN. '
    if result and (loc1 == loc2):
        return False, pars_spot, 'Self spotting'

    return result, pars_spot, reson


def rec_mufspot(compl_spot):
    """
    Input:
    (DxDateTime, DxCall1, DxLoc1, DxCall2, DxLoc2, Freq, SpotInfo, QTF1, Elev1, QRB1,
    CentrLoc, CritFreq, MUF, TryFrom, TryTo, QTF2, Elev2, QRB2, FOT, QRB_To_Midpoint, Band)

    write Es spot in base MUF
    """
# удалить лишние поля

    query = ("insert into tblspot "
             "(DxDateTime, DxCall1, DxLoc1, DxCall2, DxLoc2, Freq, SpotInfo, QTF1, Elev1, QRB1,"
             "CentrLoc, CritFreq, MUF, TryFrom, TryTo, QTF2, Elev2, QRB2, FOT, QRB_To_Midpoint, Band, Mode)"
             "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

    res, conn = base_connect(**db_config)
    if res is True:
        curs = conn.cursor()
        try:
            curs.execute(query, compl_spot)
        except Error:
            res = False
        else:
            conn.commit()
        finally:
            curs.close()
            conn.close()

    return res


def rec_allspot(pasr_spot):
    """
    Input: [date, spotter, loc1, dx, loc2, freq, comment, prop, mode, qrb]
    """

    query = ("insert into tblallspot "
             "(date, spotter, loc1, dx, loc2, freq, comment, prop, mode, qrb) "
             "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

    res, conn = base_connect(**db_config)
    if res is True:
        curs = conn.cursor()
        try:
            curs.execute(query, pasr_spot)
        except Error:
            res = False
        else:
            conn.commit()
        finally:
            curs.close()
            conn.close()

    return res


if __name__ == '__main__':

    if get_prop_list():
        print('Propagation list loaded')
    else:
        print('Testing impossible')
        sys.exit()
    # ************************ _find_mode TEST ************************
    print('Test function find_mode')
    test_sets = [
        ['Tnx for QSO', 70.1549, 'FT8'],
        ['    JN66OA<TR>JN12LL cw519QSB-BCN  1122Z', 144.1741, 'FT8'],
        ['    JN66OA<TR>JN12LL cw519QSB-BCN  1122Z', 144.4761, 'UNKNOWN'],
        ['    JN66OA<TR>JN12LL cw519QSB-BCN  1122Z', 144.1761, 'JT65'],
        ['          CW     6 dB  26 WPM  CQ      1305Z', 28.0367, 'CW'],
        ['               tnx so much Tamas 599  1249Z', 144.3000, 'CW'],
        ['                    JN45<tr>JN12 ssb 0032Z', 50.0663, 'SSB'],
        ['             cw     JN45<tr>JN12     0032Z', 50.0663, 'CW'],
        ['    CW              JN45<tr>JN12     0032Z', 50.0663, 'CW'],
        ['        559, ANY DX calling 234', 1296.85, 'CW'],
        ['FT4  Tnx for QSO', 28.18, 'FT4'],

                ]
    for test_set in test_sets:
        test_find_mode(test_set)

    # ************************ find_par TEST *************************
    print('\r\n\r\nTest function find_par')
    test_sets = [
        ['JO22NU(TR)IO93 559', 'TROPO'],
        ['        CQ CQ CQ ARRL DX SSB', 'UNKNOWN'],
        ['IN88IJ < TR > JO31LH FT8 B - 13 TKS', 'TROPO'],
        ['EM95NU<TEP>FF31QP 599 into NC', 'TEP'],
        ['JO01MT < RS > IO93NR - 32dBJT', 'RAIN'],
        ['KN49WV:MS:JO20KV +10db msk144   ', 'MS'],
        ['KN49:MS:JO20 +10db msk144   ', 'MS'],
        [' 57A jn62hk', 'AU'],
        ['          IO85BU(RS)IO94BP 539', 'RAIN'],
        ['53S JN37UP < RS > JN55FO via JN55', 'RAIN'],
        ['jn78dj<rs>jo50vi 52s v ', 'RAIN'],
        ['IO86MN(MS)IO80XS 57s', 'MS'],
        ['jo80jg<tr>jo70db 579 180 km', 'TROPO'],
        ['JO22IP(TR)IO93IR 559', 'TROPO'],
        ['KP05-ES-JO43', 'ES'],
        ['io92 ES kp32 clg a GW3', 'ES'],
        ['KP23<ES<JO61', 'ES'],
        ['JO43:Es:KP36OI  weak', 'UNKNOWN'],
        ['<TR> FT8 -14 dB 1550 Hz CQ', 'TROPO'],
        ['Jn86dr(EME)KN22TK  -15db TNX', 'EME'],
        ['319-529 qsb + AS', 'AS'],
        ['jm77ne>ES<JO40LN', 'ES'],
                 ]

    for test_set in test_sets:
        test_find_par(test_set)

# TODO: написать тест для разбора спота
#
    result, spot = r.spot_parse('DX de UT4UEP:      144360.120 OQ4U           KN49WV:MS:JO20KV +10db msk144   1658z')
    if result:
        result, pars_spot, reson = spot_processed(spot)
    # result, pars_spot, reson = spot_processed(
    #     'DX de F6ANO:     144174.0 EB1B         Ge Carlos Tks QSO & Gd DX      1658Z')
        print('\n', result, pars_spot, reson)
