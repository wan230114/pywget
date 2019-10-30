# -*- coding: utf-8 -*
# @Author: ChenJun
# @Email:  chenjun2049@foxmail.com
# @Qmail:  1170101471@qq.com
# @Date:   2019-09-08 17:24:02
# @Last Modified by:   JUN
# @Last Modified time: 2019-10-24 20:08:12

import argparse
import sys
import os
import getpass
import re
import time
import datetime
import requests
import json
import struct
from socket import *
from packages.pywget_funcs import pywget_funcs


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
    parser.add_argument('-c', '--complete', action='store_true', default=False,
                        help='当下载文件存在时是否跳过询问直接覆盖')
    args = parser.parse_args()
    print(args)
    return args.__dict__


class pywget(pywget_funcs):
    '''download file function'''

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
        print('[url]:', self._url)
        url, filename, force, block = self._url, self.filename, self.force, self._block
        if not filename:
            filename = self.__remove_nonchars__(url.split('/')[-1])
        local_filename = self.__remove_nonchars__(filename)
        tmp_filename = local_filename + '.downtmp'
        self.local_filename, self.tmp_filename = local_filename, tmp_filename

        # 此处应该判断文件大小是否完整
        stat = self.__support_continue__(url)  # 如果支持断点续传
        if os.path.exists(local_filename):
            if stat:
                # 判断缓存文件是否存在
                try:
                    with open(tmp_filename, 'rb') as fin:
                        self._size = int(fin.read())
                except Exception as e:
                    print('获取已下载字节数报错，已重置下载文件')
                    self.__touch__(local_filename)
                    self.__touch__(tmp_filename)
            elif os.path.getsize(local_filename) == self._size_total:
                # 判断下载的文件长度是否完全
                if not force:
                    print('下载文件已存在，%s' % local_filename)
                    print('请求返回字节数与文件大小相等，为:', self._size_total)
                    print('已跳过下载')
                    return
                    # try:
                    #     if input('是否覆盖文件？(回车-->覆盖，任意字符串退出)：'):
                    #         sys.exit(1)
                    # except OSError:
                self.__touch__(local_filename)
        else:  # 否则重建文件
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
            print("Downloading...")
            if self._size_total > 0:
                print("[+] Size: %s" % self.__getsize__(self._size_total - self._size))
            else:
                print("[+] Size: None")
            self._size2 = self._size  # 记录此时获得了多少数据
            _size2_last = self._size2
            with open(local_filename, 'ab+') as f:
                f.seek(self._size if self._size == 0 else self._size - 1)
                f.truncate()
                n = 0.1
                time_start = datetime.datetime.now()
                t0 = time.time()
                for chunk in iters:
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        self._size2 += len(chunk)
                        # print(size, self._size_total, n)
                        do = 0
                        if self._size2 / self._size_total > n:
                            n += 0.05
                            do = 1
                        elif (self._size2 - _size2_last) // (20 * 1024 ** 2):
                            do = 1
                        if do and (time.time() - t0 > 0.5):
                            sys.stdout.write('Now: %s, Total: %s, Download Speed: %s%s' % (
                                self.__getsize__(self._size2),
                                self.__getsize__(self._size_total),
                                '%-11s' % ('%s/s' % self.__getsize__(
                                    (self._size2 - _size2_last) / (time.time() - t0))),
                                self._speed_end))
                            sys.stdout.flush()
                            t0 = time.time()
                            _size2_last = self._size2
                if self._size_total == self._size2:
                    finished = True
                    os.remove(tmp_filename)
                    time_spend = datetime.datetime.now() - time_start
                    speed_tmp = self.__getsize__(self._size2 - self._size)
                    speed = float(speed_tmp[:-1]) / (
                        time_spend.total_seconds() if time_spend.total_seconds() else 1)
                    sys.stdout.write(
                        '[Download Finished]!\n[Total Time]: %s\n[Download Speed]: %.3f%s/s\n' % (
                            time_spend, speed, speed_tmp[-1]))
                    sys.stdout.flush()
                else:
                    print('WARNING, 下载可能未完成，已下载(b)/总下载(b)：', self._size2, '/', self._size_total)
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            if not finished:
                with open(tmp_filename, 'w') as tmp:
                    tmp.write(str(self._size2))
                print("\nDownload pause.\n")
                raise


def main():
    kwargs = fargv()
    pywget(kwargs).download()

    # pywget({'url': 'http://cd15-c120-1.play.bokecc.com/flvs/cb/QxEZF/hIZrEKBTdq-2.pcf?t=1570436774&key=C98D110A66E8B92F34D54244D2676754&tpl=10&tpt=111',
    #         'headers': {"Referer": "http://www.tmooc.cn/player/index.shtml?courseId=5DF587D41C7C40759DEAF911C5C7B188",
    #                     "Sec-Fetch-Mode": "no-cors",
    #                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36"},
    #         'filename': 'test.pcf',
    #         'force': True}).download()


if __name__ == '__main__':
    # pywget({'url': 'http://118.89.194.65/genome.gff3.idx'}).download()
    # sys.exit()
    main()
