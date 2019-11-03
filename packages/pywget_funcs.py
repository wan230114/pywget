'''
存储基本功能的模块
'''
import sys
import os
import getpass
import re
import time
import requests
import json
import struct
from socket import *


class pywget_funcs:
    '''
    base funcs
    '''

    def __init__(self, config={}):
        self._url = config.get('url', None)
        self.filename = config.get('filename', None)
        self.force = config.get('force', False)
        self._speed_end = '\n' if config.get('complete', False) else '\r'
        self._block = int(config.get('block', 1024))
        self._headers = config.get(
            'headers', {"User-Agent": "Wget/1.12 (cygwin)", "Accept": "*/*"})
        self._proxy = config.get('proxy', None)
        self._sock = self.__server_Connect__(
            self._proxy) if self._proxy else False
        self._stat = 0  # 记录是否支持断点续传
        self._size = 0  # 记录断点位置字节数
        self._size2 = 0  # 记录此时获得了多少字节数据
        self._size_recved = 0  # 接收的字节数
        self._size_total = 0  # 需要下载的文件总字节数

    def __touch__(self, filename):
        '''clean file'''
        with open(filename, 'w+') as fin:
            print('touch_file:', filename)

    def __remove_nonchars__(self, path_name):
        '''clean name'''
        name = os.path.basename(path_name)
        dirname = os.path.abspath(os.path.dirname(path_name))
        newname, n = re.subn(r'[\\/:*?"\'<>|]', '_', name)
        if n:
            print('file renamed: %s --> %s' % (name, newname), '替换了', n, '次')
        os.makedirs(dirname, exist_ok=True)
        return os.sep.join([dirname, name])

    def __support_continue__(self, url):
        '''test url'''
        try:
            r = requests.head(url, headers=self._headers)
            crange = r.headers['content-range']
            self._size_total = int(
                re.match(r'^bytes 0-\d+/(\d+)$', crange).group(1))
            return 1
        except Exception:
            try:
                self._size_total = int(r.headers['content-length'])
            except Exception:
                self._size_total = 0
        print('获取到文件长度:', self._size_total)
        return 0

    def __myrecv__(self):
        '''获取结构化数据，即：获取报头，解析报头，到真实数据'''
        ll = self.__recv_size__(4)  # 1.获取报头
        header_size = struct.unpack('i', ll)[0]  # 2.解析报头
        header_json = self.__recv_size__(header_size).decode('utf-8')  # 3.接收报文
        header_dic = json.loads(header_json)  # 4.解析报文
        size = header_dic['size']  # 5.获取真实数据的长度
        return self.__recv_size__(size)

    def __mysend__(self, msg):
        '''发送带报头信息的信息'''
        s = self._sock
        header_dic = {'size': len(msg)}  # 1.包装报文
        header_json = json.dumps(header_dic).encode('utf-8')  # 2.处理报文
        s.send(struct.pack('i', len(header_json)))  # 3.发送报头
        s.send(header_json)  # 4.发送报文
        s.send(msg)  # 5.发送真实的数据

    def __do_recv__(self):
        '''down'''
        print('[using proxy server]')
        # 发送请求开始信号，辨别身份
        self._sock.send(b'[send-url]')
        # 0) 发送网址信息
        print('[send-url]%s[%s]' % (self._url, getpass.getuser()))
        self.__mysend__(('[send-url]%s[%s]' %
                         (self._url, getpass.getuser())).encode())
        print(time.strftime("[%Y-%m-%d %H:%M:%S, Content Success]",
                            time.localtime()))
        print('正在排队...')

        # 1) 接收断点续传信息和开始信息
        msg = self.__recv_size__(8).decode()
        if int(msg[0]):
            self._stat = 1
            self.__support_continue_do__(True)
        if msg[1:] == '[start]':
            print('排队结束, 下载中...')
        else:
            print(msg)
            print('ConnectionError: [start]single not correct')
            sys.exit(1)

        # 2) 发送网页请求头
        self.__mysend__(json.dumps(self._headers).encode('utf-8'))

        # 3) 接收文件总长度
        self._size_total = int(self.__myrecv__())
        self._size_recved = 0
        print('[文件总大小:', self._size, '/', self._size_total,
              self.__getsize__(self._size_total), ']')

    def __do_recv2__(self):
        '''传输下载的生成器'''
        n = 0
        t0 = time.time()
        while True:
            ll = self.__recv_size__(4)
            if ll == b'[ok]':
                stime = time.time() - t0
                hsize = self.__getsize__(self._size_recved)
                print('\n[下载总大小:', self._size_total,
                      self.__getsize__(self._size_total), ']')
                print('\n下载完毕',
                      time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                      '\n耗时%.3fs' % (stime),
                      '平均速度: %.3f%s/s' %
                      (float(hsize[:-1]) / stime, hsize[-1]),
                      sep='\n')
                break
            elif ll == b'[FL]':
                print('\n下载字节数不统一可能未完成，已下载 %s / %s' %
                      (self._size_recved, self._size_total))
                break
            # 1、得到size
            header_size = struct.unpack('i', ll)[0]
            # 2、接收报文
            header_json = self.__recv_size__(header_size).decode('utf-8')
            # 3、解析报文
            header_dic = json.loads(header_json)
            # 4、获取真实数据的长度
            check_size = header_dic['size']
            self._size_recved += check_size
            # 5、获取数据
            yield (self.__recv_size__(check_size))

    def __getsize__(self, size):
        '''get size'''
        D = {0: 'B', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        for x in D:
            if int(size) < 1024 ** (x + 1):
                hsize = str('%.3f' % (int(size) / 1024 ** x)) + D[x]
                return hsize

    def __server_Connect__(self, proxy):
        '''connect server
        proxy: 118.123.21.34:8088'''
        HOST, PORT = proxy.split(':')
        ADDR = (HOST, int(PORT))
        s = socket()  # tcp套接字创建,默认参数即可
        setdefaulttimeout(10)  # 设置超时时间
        time = 3
        for i in range(time):
            try:
                s.connect(ADDR)
                break
            except (ConnectionRefusedError, timeout):
                print(
                    'Warning: Connect Failed. An error has occurred on the server. Please check server.')
                raise
        s.setsockopt(SOL_SOCKET, SO_RCVBUF, 0)  # 设置缓冲区
        return s

    def __recv_size__(self, len_s):
        '''接收指定长度的信息，处理tcp的收发缓冲区导致的接受不完全问题'''
        s = self._sock
        # print('01start', len_s)
        L = []
        recv_size = 0
        while recv_size < len_s:
            size = len_s - recv_size
            # print('will-->', size)
            msg = s.recv(size)
            if not msg:
                break
            recv_size += len(msg)
            L.append(msg)
        # print('\n---------------\n', b''.join(L), '\n------------\n')
        assert (recv_size == len_s), "getsize != len_s, %s/%s" % (recv_size, len_s)
        return b''.join(L)

    def __getRequests__(self, _url):
        '''访问并获取iters'''
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        # 禁用安全请求警告
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        r = requests.get(_url, stream=True,
                         verify=False, headers=self._headers)
        n = 0
        url = _url
        while (url not in r.url) and n < 20:
            n += 1
            url = r.url
            print('第', n, '次跳转', self._url, r.url)
            r = requests.get(url, stream=True,
                             verify=False, headers=self._headers)
        if n >= 20:
            raise Exception('跳转次数大于20次，请检查请求地址是否正确')
        return r
