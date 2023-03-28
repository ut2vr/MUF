[Station]
call = <CALL>
loc = <DX Locator>

[Source]
dx cluster server = dxmaps.com
# dx cluster server = eadx.org
dx cluster port = 7300
rbn cw server = telnet.reversebeacon.net
rbn cw port = 7000
rbn ft8 server = telnet.reversebeacon.net
rbn ft8 port = 7001
rp ft8 server = <IP ADDR>
rp ft8 port = <PORT>
# Time to reactivate telnet connection (min)
reconnect time = 50
prop mask = ES
mode mask = CW

[Setting]
Server port = 7300
RP FT8 = NO

# 50 critical()
# 40 error()
# 30 warning() обрыв соединения, не нулевая длина очереди, спот не разобран, соединение закрыто с потоком

# 20 info()     соединение установлено, отправлен спот

# 10 debug()

log level = 10


[MySQL]
host = <IP ADDR>>
database = MUF
user = <USER_NAME>
password = <PASSWD>

[Mail]
mailhost = smtp.ukr.net
mailport = 465
fromaddr = <E-MAIL>
toaddr = <E-MAIL>
suject = Error
credentials_name = <USER_NAME>
credentials_passwd = <PASSDW>
