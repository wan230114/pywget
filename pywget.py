# -*- coding: utf-8 -*
# @Author: ChenJun
# @Email:  chenjun2049@foxmail.com
# @Qmail:  1170101471@qq.com
# @Date:   2019-09-08 17:24:02
# @Last Modified by:   JUN
# @Last Modified time: 2019-10-07 18:03:30

import argparse
import sys
import os
import re
import time
import requests
import getpass
import json
import struct
from socket import *


def fargv():
    parser = argparse.ArgumentParser(description='用于下载文件的程序.')
    parser.add_argument('url', type=str,
                        help='输入需要下载的文件网址')
    parser.add_argument('-o', '--filename', type=str, default=None,
                        help='输出的下载文件的name')
    parser.add_argument('-p', '--proxy', type=str, default=None,
                        help='代理服务端的IP及端口，如：118.96.72.54:8668')
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='当下载文件存在时是否跳过询问直接覆盖')
    args = parser.parse_args()
    return args.__dict__


class pywget:
    '''download file function'''

    def __init__(self, config={}):
        self._url = config['url']
        self._block = int(config.get('block', 1024))
        self._headers = config.get(
            'headers', {"User-Agent": "Wget/1.12 (cygwin)", "Accept": "*/*"})
        self._proxy = config.get('proxy', None)
        self._sock = self.__server_Connect__(self._proxy) if self._proxy else False
        self._size = 0  # 记录断点位置字节数
        self._size_recved = 0  # 接收的字节数
        self._size_total = 0  # 需要下载的文件总字节数
        self.filename = config.get('filename', None)
        self.force = config.get('force', False)

    def __remove_nonchars__(self, path_name):
        '''clean name'''
        name = os.path.basename(path_name)
        dirname = os.path.abspath(os.path.dirname(path_name))
        newname, n = re.subn('[\\\/\:\*\?\"\<\>\|]', '', name)
        if n:
            print('file renamed: %s --> %s' % (name, newname), n)
        os.makedirs(dirname, exist_ok=True)
        return os.sep.join([dirname, name])

    def __touch__(self, filename):
        '''clean file'''
        with open(filename, 'w+') as fin:
            print('touch_clean_file:', filename)

    def __support_continue__(self, url):
        '''test url'''
        try:
            r = requests.head(url, headers=self._headers)
            crange = r.headers['content-range']
            self._size_total = int(re.match(r'^bytes 0-\d+/(\d+)$', crange).group(1))
            return True
        except Exception:
            pass
        try:
            self._size_total = int(r.headers['content-length'])
        except Exception:
            self._size_total = 0
        return False

    def __support_continue_do__(self, stat):
        '''do continue'''
        local_filename, tmp_filename = self.local_filename, self.tmp_filename
        if stat:  # 支持断点续传
            print('[stat]支持断点续传')
        else:
            print('[stat]下载不支持断点续传，已重置下载文件')
            self.__touch__(tmp_filename)
            self.__touch__(local_filename)
        if self._size != 0:
            headers_range = "bytes=%d-" % (self._size - 1)
            # headers_range = "bytes=%d-" % (self._size if self._size == 0
            #                                else self._size - 1)
            self._headers.update(headers_range)

    def __getsize__(self, size):
        '''get size'''
        D = {0: 'B', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        for x in D:
            if int(size) < 1024**(x + 1):
                hsize = str('%.3f' % (int(size) / 1024**x)) + D[x]
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
                print('Warning: Connect Failed. An error has occurred on the server. Please check server.')
                raise
        s.setsockopt(SOL_SOCKET, SO_RCVBUF, 0)  # 设置缓冲区
        return s

    def __recv_size__(self, len_s):
        '''处理tcp的收发缓冲区导致的接受不完全问题'''
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

    def __myrecv__(self):
        ll = self.__recv_size__(4)  # 1.获取报头
        header_size = struct.unpack('i', ll)[0]  # 2.解析报头
        header_json = self.__recv_size__(header_size).decode('utf-8')  # 3.接收报文
        header_dic = json.loads(header_json)  # 4.解析报文
        size = header_dic['size']  # 5.获取真实数据的长度
        return self.__recv_size__(size)

    def __mysend__(self, msg):
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
        self.__mysend__(('[send-url]%s[%s]' % (self._url, getpass.getuser())).encode())
        print(time.strftime("[%Y-%m-%d %H:%M:%S, Content Success]",
                            time.localtime()))
        print('正在排队...')

        # 1) 接收断点续传信息和开始信息
        msg = self.__recv_size__(8)
        if int(msg[0]):
            self.__support_continue_do__(True)
            # print(headers_range)
        if msg[1:] == b'[start]':
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
        n = 0
        t0 = time.time()
        while True:
            ll = self.__recv_size__(4)
            if ll == b'[ok]':
                stime = time.time() - t0
                hsize = self.__getsize__(self._size_recved)
                print('\n[下载总大小:', self._size_total, self.__getsize__(self._size_total), ']')
                print('\n下载完毕',
                      time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                      '\n耗时%.3fs' % (stime),
                      '平均速度: %.3f%s/s' %
                      (float(hsize[:-1]) / stime, hsize[-1]),
                      sep='\n')
                break
            elif ll == b'[FL]':
                print('下载失败，已下载 %s / %s' % (self._size_recved, self._size_total))
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

    def download(self):
        '''主程序'''
        # 1) 文件准备
        finished = False
        print('Download start:')
        url, filename, force, block = self._url, self.filename, self.force, self._block
        if not filename:
            filename = self.__remove_nonchars__(url.split('/')[-1])
        local_filename = self.__remove_nonchars__(filename)
        tmp_filename = local_filename + '.downtmp'
        try:
            with open(tmp_filename, 'rb') as fin:
                self._size = int(fin.read())
        except Exception as e:
            # print('WARNING:', e)
            self.__touch__(tmp_filename)
        self.local_filename, self.tmp_filename = local_filename, tmp_filename

        if os.path.exists(local_filename) and not os.path.exists(tmp_filename):
            if not force:
                print('下载文件已存在，%s' % local_filename)
                try:
                    if input('是否覆盖文件？(回车-->覆盖，任意字符串退出)：'):
                        sys.exit(1)
                except OSError:
                    print('文件已存在，已跳过下载')
                    sys.exit(1)
            else:
                self.__touch__(local_filename)

        # 2) 请求开始
        try:
            if not self._sock:
                self.__support_continue_do__(self.__support_continue__(url))
                r = requests.get(self._url, stream=True, verify=False, headers=self._headers)
                iters = r.iter_content(chunk_size=block)
            else:
                self.__do_recv__()
                iters = self.__do_recv2__()
            start_t = time.time()
            if self._size_total > 0:
                print("[+] Size: %s" % self.__getsize__(self._size_total - self._size))
            else:
                print("[+] Size: None")
            print("Downloading...")
            self._size2 = self._size
            with open(local_filename, 'ab+') as f:
                f.seek(self._size if self._size == 0 else self._size - 1)
                f.truncate()
                n = 0.1
                for chunk in iters:
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        self._size2 += len(chunk)
                        try:
                            # print(size, self._size_total, n)
                            if self._size2 / self._size_total > n:
                                n += 0.05
                                sys.stdout.write('Now: %s, Total: %s\n' %
                                                 (self.__getsize__(self._size2),
                                                  self.__getsize__(self._size_total)))
                                sys.stdout.flush()
                        except ZeroDivisionError:
                            pass
                finished = True
                os.remove(tmp_filename)
                spend = time.time() - start_t
                speed_tmp = self.__getsize__(self._size2 - self._size)
                speed = float(speed_tmp[:-1]) / (spend if spend else 1)
                sys.stdout.write(
                    '\nDownload Finished!\nTotal Time: %.3fs, Download Speed: %.3f%s/s\n' % (spend, speed, speed_tmp[-1]))
                sys.stdout.flush()
        except Exception:
            import traceback
            print(traceback.print_exc())
            print("\nDownload pause.\n")
        finally:
            if not finished:
                with open(tmp_filename, 'w') as ftmp:
                    ftmp.write(str(self._size2))


def main():
    kwargs = fargv()
    # kwargs['url'] = 'http://118.89.194.65/genome.gff3.idx'
    pywget(kwargs).download()
    # pywget({'url': 'http://cd15-c120-1.play.bokecc.com/flvs/cb/QxEZF/hIZrEKBTdq-2.pcf?t=1570436774&key=C98D110A66E8B92F34D54244D2676754&tpl=10&tpt=111',
    #         'headers': {"Referer": "http://www.tmooc.cn/player/index.shtml?courseId=5DF587D41C7C40759DEAF911C5C7B188",
    #                     "Sec-Fetch-Mode": "no-cors",
    #                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36"},
    #         'filename': 'test.pcf',
    #         'force': True}).download()


if __name__ == '__main__':
    main()
