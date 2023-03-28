#!/usr/bin/python3
# coding:utf-8

import logging
import logging.handlers
import telnetlib
import queue
import muf_base
import configparser
import os
import radio as r
import threading
from datetime import datetime
import socket
import time
import sys
from email.message import EmailMessage
import email.utils
import smtplib


def dxc(call, host, port):
    """
    Telnet connection to DX Cluster
    """
    prev = 'nothing'  # вставлено для проверки
    dxc_conn = 0
    dx = None
    while True:
        while dxc_conn == 0:
            t1 = time.time()
            logger.debug('dxc_conn = {0} {1:%H:%M:%S}'.format(dxc_conn, datetime.now()))
            time.sleep(10)
            try:
                dx = telnetlib.Telnet(host, port)
            except (OSError, EOFError) as err:
                logger.warning('conn= {0} {1}:{2}'.format(dxc_conn, host, port))
                logger.warning("{0}. Wait 120sec.".format(err))
                time.sleep(120)
                break
            else:
                dxc_conn = 1

        while dxc_conn == 1:
            logger.debug('dxc_conn = {0} {1:%H:%M:%S}'.format(dxc_conn, datetime.now()))
            try:
                dxc_resp = dx.read_until(b"\n", 1)
            except (OSError, EOFError) as err:
                logger.error('conn= {0} {1}:{2}'.format(dxc_conn, host, port))
                logger.error(err)
                time.sleep(10)
                dxc_conn = 0
                dx.close()
                break
            if b"login: " in dxc_resp:
                dx.write(call.encode() + b"\n")
                try:
                    dxc_resp = dx.read_until(b"dxspider >\n", 4)    # сколько ждать? *********************
                except (OSError, EOFError) as err:
                    logger.error('conn= {0} {1}:{2} {3}'.format(dxc_conn, host, port, err))
                    dxc_conn = 0
                    dx.close()
                    break
                else:
                    dxc_conn = 2
                    logger.info('DX Cluster:  {0}:{1}  connected'.format(host, port))
                    t1 = time.time()
        while dxc_conn == 2:
            try:
                out_spot = out_spotQueue.get(block=False)
            except queue.Empty:
                pass
            else:
                logger.debug('-- out_spot get: {0}'.format(out_spot))
                dx.write(out_spot.encode() + b"\n")
                logger.info('Send spot (command): {0}'.format(out_spot))
                t1 = time.time()    # таймер перегрузить

            t2 = time.time() - t1
            if t2 > 60 * T:
                logger.warning('Activate ' + host)
                dxc_conn = 0
                try:
                    dx.write(b"\n")
                    dxc_resp = dx.read_until(b"\n", 1)
                except (OSError, EOFError) as err:
                    logger.error('conn= {0} {1}:{2}'.format(dxc_conn, host, port))
                    logger.error(err)
                    time.sleep(60)
                    break
                if dxc_resp == b'\n':
                    dxc_resp = dx.read_until(b"\n", 1)
                if b'dxspider >' not in dxc_resp:
                    if b"DX de" not in dxc_resp:
                        break
                t1 = time.time()
                dxc_conn = 2

            try:
                dxc_resp = dx.read_until(b"\n", 5)      # при обрыве соединения, по таймауту выдает пустую строку
            except (OSError, EOFError) as err:
                logger.warning('conn= {0} {1}:{2}'.format(dxc_conn, host, port))
                logger.warning(err)
                dxc_conn = 0
                dx.close()
                break
            else:
                # print(dxc_resp)
                ind = dxc_resp.find(b"\a\a")    # проверить на обрывки строк
                if ind > 0:
                    logger.debug('*: {0}'.format(dxc_resp))
                    try:
                        s = dxc_resp[:ind].decode(errors='replace')  # encoding='cp1256', errors='replace')
                    except UnicodeDecodeError as err:
                        logger.error(err)
                        continue
                    result, spot = r.spot_parse(s)

                    if result:
                        if raw_spotQueue.qsize() > 0:
                            logger.warning('raw_spotQueue {0}'.format(raw_spotQueue.qsize()))
                        if raw_spotQueue.qsize() > 10:
                            os.system("sudo reboot")
                            # sys.exit()      # reboot system поискать проблему в filtr_spot()
                        raw_spotQueue.put(spot)
                        prev = s  # вставлено для проверки
                        logger.debug('- dxc put: {0}'.format(spot))
                    else:
                        logger.warning('prev. string: {0}'.format(prev))    # вставлено для проверки
                        logger.warning('unrecognized: {0}'.format(s))
        if stop_dxc.is_set():
            dx.close()
            logger.warning('DX Cluster:  {0}:{1}  connection close'.format(host, port))
            break


def rp_skim(callsign, host, port, lfreq, hfreq):
    """
    Telnet connection to Red Pitaya FT8 Skimmer
    """
    connected = 0
    dx = None
    s = ''
    while True:
        while connected == 0:
            try:
                dx = telnetlib.Telnet(host, port)
            except (OSError, EOFError) as err:
                logger.error('conn= %s %s:%s', str(connected), host, port)
                logger.error(err)  # [Errno 113] No route to host
                if err.args[0] == 113:
                    stop_rp.set()
                    break
            else:
                connected = 1
                logger.warning('RP FT8 skimmer: %s:%s connected', host, port)
        while connected == 1:
            try:
                respone = dx.read_until(b"\n", 4)  # connection close
            except (OSError, EOFError) as err:
                logger.error('conn= %s %s:%s', str(connected), host, port)
                logger.error(err)
                connected = 0
                dx.close()
            else:
                if b"FT8 Skimmer >" in respone:
                    connected = 2
        while connected == 2:
            try:
                respone = dx.read_until(b"\n", 4)
            except (OSError, EOFError) as err:
                logger.error('conn= %s %s:%s', str(connected), host, port)
                logger.error(err)
                connected = 0
                dx.close()
            else:
                if b"DX de" in respone:  # 17:30
                    ind = respone.find(b":")
                    try:
                        s = respone[ind + 1:25].decode()
                        fr = s.lstrip()
                        freq = float(fr)
                    except (UnicodeDecodeError, ValueError) as err:
                        logger.error('%s:%s  freq= %s', host, port, s)
                        logger.error(err)
                    else:
                        try:
                            s = respone.decode()
                        except UnicodeDecodeError as err:
                            logger.error('Spot: %s', respone)
                            logger.error('%s:%s %s', host, port, err)
                        else:
                            ind = s.find("\r")
                            ind1 = s.find("\n")
                            spot = s[ind + 1:ind1]
                            if ((freq == 50313.0) or (freq == 50323)) and (RP_present == 'YES'):
                                dxcall = spot[24:38].strip()
                                loc = muf_base.find_loc_base(dxcall)
                                if loc == 'UNKNOWN':
                                    continue
                                dist = r.distance(hloc, loc)
                                if dist < 2200:
                                    continue

                                line = spot[38:70].strip()
                                ind = line.find(' dB ')
                                line = line[:ind+4]
                                comment = line[3:]
                                out_spot = 'DX {0} {1} {2}<ES>{3} {4} hrd'.format(fr, dxcall, hloc, loc, comment)

                                logging.debug('- RP out_spot put: {0}'.format(out_spot))
                                out_spotQueue.put(out_spot)
                                continue    # в базу попадет через DXSpider
                            if (freq > lfreq) and (freq < hfreq):
                                result, sp = r.spot_parse(spot)
                                raw_spotQueue.put(sp)
                                logging.debug('- RP raw_spot put: {0}'.format(sp))

        if stop_rp.is_set():
            dx.close()
            logger.warning('RP Skimmer:  %s:%s  connection close', host, port)
            break


def rbn(callsign, host, port, lfreq, hfreq):
    """
    Telnet connection to Reverce Beacon network
    """
    connected = 0
    rb = None
    while True:
        while connected == 0:
            try:
                rb = telnetlib.Telnet(host, port, 3)
            except (OSError, EOFError) as err:
                logger.error('conn= %s %s:%s', str(connected), host, port)
                logger.error(err)
            else:
                connected = 1
        while connected == 1:
            respone = rb.read_until(b"\n", 1)
            if b"call" in respone:
                rb.write(callsign.encode() + b"\r\n")
                respone = rb.read_until(b">\n", 4)
                connected = 2
                logger.info('RBN:  %s:%s  connected', host, port)
        while connected == 2:
            try:
                respone = rb.read_until(b"\n", 4)
            except (OSError, EOFError) as err:
                logger.error('conn= %s %s:%s', str(connected), host, port)
                logger.error(err)
                connected = 0
                rb.close()
            else:
                if b"DX de" in respone:
                    ind = respone.find(b"\n\n")
                    try:
                        s = respone[:ind].decode()
                    except UnicodeDecodeError:
                        logger.error('UnicodeDecodeError %s:%s', host, port)
                        logger.error('Spot %s', respone[:ind])
                    else:
                        ss = s[6:24]
                        ind = ss.find(' ')
                        try:
                            freq = float(ss[ind:].lstrip())
                        except ValueError:
                            logger.error('ValueError %s:%s  freq= %s', host, port, ss[ind:].lstrip())
                        else:
                            if (freq > lfreq) and (freq < hfreq):
                                raw_spotQueue.put(s)
        if stop_dxc.is_set():
            rb.write(b"bye\n")
            rb.close()
            logger.info('DX Cluster:  %s:%s  connection close', host, port)
            break


def filtr_spot():
    """
    здесь производится парсинг, вычисление параметров MUF и фильтрация спотов
    для таблицы tblallspot и telnet клиентов: all_spotQueue
    для таблицы tblspot: muf_spotQueue
    :return: очереди записей
    """

    logger.info("Start filtration thread")

    while not stop_filtr.is_set():
        try:
            raw_spot = raw_spotQueue.get(block=False)
        except queue.Empty:
            continue
        # TODO: сделать фильтр повторов (дублей)
        logger.debug('-- filtr get: {0}'.format(raw_spot))

        result, pars_spot, reson = muf_base.spot_processed(raw_spot)

        if result is False:
            logger.warning('{0}:  {1}'.format(reson, raw_spot))
            continue

        date, spotter, loc1, dx, loc2, freq, comment, prop, mode, qrb, band = pars_spot

        if all_spotQueue.qsize() > 0:
            logger.warning('all_spotQueue {0}'.format(all_spotQueue.qsize()))

        all_spotQueue.put(pars_spot)    # передаем все обработанные споты

        if prop == 'ES':                            # в таблицу tblspot пишем только спорадик

            res, qtf1, Elev1, QRB1, CentreLoc, CritFreq, MUF, TryFrom, TryTo, Qtf2, Elev2, QRB2, FOT, Qrb_To_Midpoint\
                = r.sp_e_reflect(hloc, pars_spot)
            if res is True:
                if QRB1 > 600:
                    muf_spot = [date, spotter, loc1, dx, loc2, freq, comment, qtf1, Elev1, QRB1, CentreLoc, CritFreq,
                                MUF, TryFrom, TryTo, Qtf2, Elev2, QRB2, FOT, Qrb_To_Midpoint, band, mode]

                    if muf_spotQueue.qsize() > 0:
                        logger.warning('muf_spotQueue {0}'.format(muf_spotQueue.qsize()))

                    muf_spotQueue.put(muf_spot)
            else:
                logger.error('MUF calculation crushed')
                logger.error(pars_spot)

    logger.info('Filtr thread  stopped')


def wr_spot():
    """
    Принимает очереди со спотами
    Выводит на консоль, пишет в файл
    Передает telnet клиентам
    Пишет в таблицы базы
    """

    logger.info("Start saving to base thread")

    # *************************************************************************
    # with open('Spots.txt', 'a') as f:     # разметка полей в файле
    #     f.write('{0:16} {1:<8} {2:<9} {3:>9} {4:<9} {5:<7} {6:<5}{7:<7} {8:<7} {9:<30}\r\n'
    #             .format("Date", "Spotter", "Loc", "Freq", "Dx", "Loc", "QRB", "Prop", "Mode", "Comment"))
    # logger.info("Write to file Spots.txt")
    # *************************************************************************

    while not stop_wr.is_set():
        try:    # обработка очереди all_spot
            all_spot = all_spotQueue.get(block=False)
        except queue.Empty:
            pass
        else:
            logger.debug('--- wr get all_spot: {0}'.format(all_spot))
            mesg = ("{0[0]:%Y-%m-%d %H:%M} {0[1]:<8} {0[2]:7} {0[5]:>11} {0[3]:<8} {0[4]:7} {0[9]:>5.0f} "
                    "{0[7]:<7} {0[8]:<7} {0[6]:>30}".format(all_spot))
            with list_lock:  # раздача спотов всем telnet клиентам
                if len(clients) > 0:
                    for client in clients:
                        client[1].put(mesg.encode() + b'\r\n')
            res = muf_base.rec_allspot(all_spot[:10])  # в таблицу allspot базы MUF
            if res is False:
                logger.error('Record in table tblallspot failed')
                stop_app()
            else:
                logger.debug('--- wr put tblallspot: {0}'.format(all_spot))
            # *************************************************************************
            # print(mesg)
            # *************************************************************************
            # with open('Spots.txt', 'a') as f:  # Выводим в текстовый файл
            #     f.write(mesg + '\r\n')
            # *************************************************************************

        try:    # обработка очереди muf_spot
            muf_spot = muf_spotQueue.get(block=False)
        except queue.Empty:
            pass
        else:
            logger.debug('--- wr get muf_spot: {0}'.format(muf_spot))
            res = muf_base.rec_mufspot(muf_spot)
            if res is False:
                logger.error('Record in table tblspot failed')
                stop_app()
            else:
                logger.debug('--- wr put tblspot: {0}'.format(muf_spot))
                # *************************************************************************
                # with safeprint:     # все параметры MUF
                #     print("{0[0]:%Y-%m-%d %H:%M} {0[1]} {0[2]} {0[3]} {0[4]} {0[5]:>11} {0[6]} "
                #           "{0[7]:.1f} {0[8]:.1f} {0[9]:.1f} {0[10]} {0[11]:.1f} {0[12]:.1f} "
                #           "{0[13]} {0[14]} {0[15]:.1f} {0[16]:.1f} {0[17]:.1f} {0[18]:.1f} "
                #           "{0[19]:.1f}".format(muf_spot))
                # *************************************************************************

    logger.info('Write thread  stopped')


def client_service(c, addr, spotQueue):
    """
    поток закрывается по сигналу stop_server
    или при потытке вывода в отключенное соединение
    """

    global clientQueue, errno

    while not stop_server.is_set():
        try:
            spot = spotQueue.get(block=False)
        except queue.Empty:
            continue
        try:
            c.send(spot)
        except socket.error as err:
            if err.args[0] == errno:
                logger.info('Client {0} disconnected'.format(addr))  # выход по разрыву соединения
            break
    else:
        logger.info('Close connection: %s. stop_server signal', addr)  # выход по сигналу

    with list_lock:
        for i in range(len(clients)):
            if clients[i][2] == c:
                logger.debug('***** Connection %s delete from list', addr)
                clients.pop(i)
                break
    c.close()
    logger.info('Client thread  stopped')


def server(host, port, welkome):

    global spotQueue, client_connected

    server = socket.socket()
    try:
        server.bind((host, port))
    except OSError as err:
        if err.args[0] == 98:
            logger.error(err)
            time.sleep(60)
            try:
                server.bind((host, port))   # second attempt
            except OSError as err:
                if err.args[0] == 98:
                    logger.error(err)

    logger.info('Server on %s port %s started', host, port)
    while True:
        if stop_server.is_set():
            client_connected.clear()
            logger.info('Server on port %s shutdown', port)
            break
        server.listen(1)
        c, addr = server.accept()
        logger.info('Connection from %s', addr)
        c.send(welkome.encode() + b'\r\n')
        spotQueue = queue.Queue(10)  # очередь для спотов
        client = [threading.Thread(target=client_service, args=(c, addr, spotQueue)), spotQueue, c]
        with list_lock:
            clients.append(client)
            client[0].start()
    logger.info('Server thread  stopped')


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def stop_app():
    # TODO:  добавить контроль завершения потоков
    stop_server.set()
    time.sleep(2)
    stop_wr.set()
    time.sleep(2)
    stop_filtr.set()
    time.sleep(2)
    stop_rp.set()
    stop_dxc.set()
    time.sleep(6)   # > timeout connection
    sys.exit()

class SSLSMTPHandler(logging.handlers.SMTPHandler):
    """
    Provide a class to allow SSL (Not TLS) connection for mail handlers by overloading the emit() method
    """
    def emit(self, record):
        """
        Emit a record.
        """
        try:
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP_SSL(self.mailhost, port)
            msg = EmailMessage()
            msg['From'] = self.fromaddr
            msg['To'] = ','.join(self.toaddrs)
            msg['Subject'] = self.getSubject(record)
            msg['Date'] = email.utils.localtime()
            msg.set_content(self.format(record))
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(msg, self.fromaddr, self.toaddrs)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


if __name__ == '__main__':

    if os.path.exists(r'/home/pi/SpotCollector.py'):
        comp = 'pi'
        Path = os.path.dirname(r'/home/pi/SpotCollector.py')
    else:
        comp = 'ub'
        Path = ''

    LOG_FILENAME = os.path.join(Path, 'Collector.log')
    INI_FILENAME = os.path.join(Path, 'SpotCollector.ini')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME, maxBytes=15000, backupCount=2)
    formatter = logging.Formatter(u'%(filename)-17s [LINE:%(lineno)3d]# %(levelname)-8s [%(asctime)s]  %(message)s'
                                  , datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if not os.path.exists(INI_FILENAME):
        config = configparser.ConfigParser()
        config.add_section("Station")
        config.set("Station", "Call", "UT2VR")
        config.set("Station", "Loc", "KN69PC")
        config.add_section("Source")
        config.set("Source", "DX Cluster Server", "dxmaps.com")
        config.set("Source", "DX Cluster Port", "7300")
        config.set("Source", "RBN CW Server", "telnet.reversebeacon.net")
        config.set("Source", "RBN CW Port", "7000")
        config.set("Source", "RBN FT8 Server", "telnet.reversebeacon.net")
        config.set("Source", "RBN FT8 Port", "7001")
        config.set("Source", "RP FT8 Server", "192.168.1.16")
        config.set("Source", "RP FT8 Port", "7373")
        config.set("Source", "Reconnect Time", "30")
        config.set("Source", "Prop mask", "ES")
        config.set("Source", "Mode mask", "CW")
        config.add_section("Setting")
        config.set("Setting", "Log Level", "20")
        config.set("Setting", "RP FT8", "NO")
        config.add_section("MySQL")
        config.set("MySQL", "Host", "192.168.0.16")
        config.set("MySQL", "DataBase", "MUF")
        config.set("MySQL", "User", "mufuser")
        config.set("MySQL", "Password", "mufpasswd")
        logging.info('Create config file SpotCollector.ini')
        with open(INI_FILENAME, "w") as config_file:
            config.write(config_file)

    config = configparser.ConfigParser()
    config.read(INI_FILENAME)
    call = config.get("Station", "Call")
    hloc = config.get("Station", "Loc")
    dxchost = config.get("Source", "DX Cluster Server")
    dxcport = config.get("Source", "DX Cluster Port")
    rbhost = config.get("Source", "RBN CW Server")
    rbport = config.get("Source", "RBN CW Port")
    rbfthost = config.get("Source", "RBN CW Server")
    rbftport = config.get("Source", "RBN CW Port")
    rphost = config.get("Source", "RP FT8 Server")
    rpport = config.get("Source", "RP FT8 Port")
    T = int(config.get("Source", "Reconnect Time"))
    RP_present = config.get("Setting", "RP FT8")
    prop_mask = config.get("Source", "Prop mask")
    mode_mask = config.get("Source", "Mode mask")
    log_level = int(config.get("Setting", "Log Level"))
    base_user = config.get("MySQL", "User")
    base_host = config.get("MySQL", "Host")
    base_name = config.get("MySQL", "DataBase")
    base_passwd = config.get("MySQL", "Password")

    mailhost = config.get("Mail", "mailhost")
    mailport = config.get("Mail", "mailport")
    fromaddr = config.get("Mail", "fromaddr")
    toaddr = config.get("Mail", "toaddr")
    suject = config.get("Mail", "suject")
    credentials_name = config.get("Mail", "credentials_name")
    credentials_passwd = config.get("Mail", "credentials_passwd")

    mail_logger = logging.getLogger()
    mail_handler = SSLSMTPHandler(mailhost=(mailhost, mailport),
                                  fromaddr=fromaddr,
                                  toaddrs=[toaddr],
                                  subject=suject,
                                  credentials=(credentials_name, credentials_passwd))
    mail_handler.setLevel(logging.ERROR)
    mail_logger.addHandler(mail_handler)
    mail_handler.setFormatter(formatter)
    logger.addHandler(mail_handler)
    logger.setLevel(log_level)

    logger.info('\n\nNew start')

    db_config = muf_base.get_base_conf(INI_FILENAME)

    i = 3
    while i > 0:
        res, conn = muf_base.base_connect(db_config)
        if not res:
            logger.info('Waiting mySQL start')
            time.sleep(15)
            i -= 1
        else:
            conn.close()
            break
    else:
        logger.error('mysql is not available')
        sys.exit()
    if muf_base.get_prop_list() is True:
        logger.info('Initialise prop_list')
    else:
        logger.error('prop_list is not initialized')
        sys.exit()

    safeprint = threading.Lock()    # блокировка для вывода на консоль
    safecalc = threading.Lock()     # блокировка для вычислений

    raw_spotQueue = queue.Queue()  # очередь для сырых спотов
    pars_spotQueue = queue.Queue()  # очередь для разобранных спотов
    muf_spotQueue = queue.Queue()  # очередь для записи в базу Es spots
    all_spotQueue = queue.Queue()  # очередь для записи в базу All spots
    out_spotQueue = queue.Queue()   # очередь для отправки спота

    workers = []    # список запущеных потоков
    stop_filtr = threading.Event()
    stop_filtr.clear()
    stop_wr = threading.Event()
    stop_wr.clear()
    stop_dxc = threading.Event()
    stop_dxc.clear()
    stop_rp = threading.Event()
    stop_rp.clear()
    # stop_rbn = threading.Event()
    # stop_rbn8 = threading.Event()
    stop_server = threading.Event()
    stop_server.clear()

    fil = threading.Thread(target=filtr_spot)
    workers.append(fil)
    fil.start()

    wr = threading.Thread(target=wr_spot)
    workers.append(wr)
    wr.start()

    dx = threading.Thread(target=dxc, args=(call, dxchost, dxcport))
    workers.append(dx)
    dx.start()

    if RP_present == 'YES':
        tmp = threading.Thread(target=rp_skim, args=(call, rphost, rpport, 50000, 52000))
        workers.append(tmp)
        tmp.start()

    # tmp = threading.Thread(target=rbn, args=(call, rbhost, rbport, lfreq, hfreq)
    # workers.append(tmp)
    # tmp.start()   # Проблема блокировки     stop_rbn = threading.Event()
    # ( запуск из одной функции )

    # tmp = threading.Thread(target=rbn, args=(call, rbhost, rbftport, lfreq, hfreq))
    # workers.append(tmp)
    # tmp.start()

    out_spotQueue.put("rej/spot on 0/28000\n")
    out_spotQueue.put("rej/ann all\n")
    out_spotQueue.put("rej/WCY all\n")
    out_spotQueue.put("rej/WWV all\n")

    serv_host = get_ip()  # Get local machine IP
    serv_port = 7300                # Reserve a port for your service.
    # errno = 10053                     #  Windows
    errno = 32
    welkome = 'UT2VR spot collector >'

    server_thread = threading.Thread(target=server, args=(serv_host, serv_port, welkome), daemon=True)
    server_thread.start()
    clientQueue = queue.Queue(10)
    client_connected = threading.Event()
    list_lock = threading.Lock()
    clients = []

    for work in workers:
        work.join()


