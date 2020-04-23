# -*- coding: utf-8 -*-
# @Author: ChenJun
# @Email:  chenjun4663@novogene.com
# @Qmail:  1170101471@qq.com
# @Date:   2019-06-23 00:27:09
# @Last Modified by:   11701
# @Last Modified time: 2019-09-11 23:40:35

import socket
import argparse
import time
import traceback
import re
import json
import struct
from packages.pywget_funcs import pywget_funcs, RequestErro


def fargv():
    parser = argparse.ArgumentParser(description='服务端的运行程序')
    parser.add_argument('proxy', nargs='?', type=str, default="0.0.0.0:8080",
                        help='代理地址及端口， 默认为 0.0.0.0:8080')
    args = parser.parse_args()
    return args.__dict__


print0 = print


def print(*args, **kwargs):
    kwargs.update({'flush': True})
    print0(*args, **kwargs)


class pywgetServer(pywget_funcs):

    def __s_getsocket__(self, proxy, CHECK_TIMEOUT=30):
        '''创建套接字，创建链接，创建父子进程　功能函数调用'''
        HOST, PORT = proxy.split(':')
        # ADDR = ('0.0.0.0', 8080)  # server address
        ADDR = (HOST, int(PORT))
        # 创建tcp套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        s.settimeout(CHECK_TIMEOUT)
        # self.test_t0 = time.time()  # 时间测试
        # socket.setdefaulttimeout(10)  # 设置超时时间

        # 在绑定前调用setsockopt让套接字允许地址重用
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 绑定
        s.bind(ADDR)
        # 设置监听
        s.listen(5)
        # s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)  # 设置缓冲区
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO,
                     struct.pack("ll", 5, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO,
                     struct.pack("ll", 5, 0))
        return s

    def do_parent(self, proxy):
        print('Run in', proxy)
        while True:
            try:
                self._sock_s = self.__s_getsocket__(proxy)
                self._size_NOW = 0
                connfd = None
                connfd, addr = self._sock_s.accept()
                self._sock = connfd
                self._sock.settimeout(10)
                # 0) 接收请求
                msg = connfd.recv(10)
                if msg.startswith(b'[send-url]'):
                    # 0) 接收url请求
                    msg = self.__myrecv__().decode()  # 接收url
                    print("\nConnect from", addr)
                    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                    url, who = re.findall(r'\[send-url\](.*)\[(.*)\]', msg)[0]
                    print('收到url请求: ', msg, '\n转发中:', url, who)

                    # 1) 发送请求状态，是否可以续传，开始信息
                    print('step: 0 ', end='')
                    # 请求状态
                    try:
                        stat = self.__support_continue__(url)
                        connfd.send(b'[OK]')
                    except RequestErro as e:
                        connfd.send(b'[ER]')
                        e = str(e)
                        self.__mysend__(e.encode('utf-8'))
                        raise RequestErro(e)
                    print('> 1 ', end='')
                    # 续传和开始信息
                    connfd.send(('%s[start]' % stat).encode('utf-8'))

                    # 2) 接收网页请求头
                    print('> 2 ', end='')
                    self._headers = json.loads(self.__myrecv__())

                    # 3) 发送下载文件长度
                    print('> 3 ', end='')
                    self.__mysend__(str(self._size_total).encode('utf-8'))

                    # 4) 升级报头
                    print('> 4 ', end='')
                    if stat:
                        _size = int(json.loads(self.__myrecv__()))
                        self._headers.update({'Range': 'bytes=%d-' % _size})
                    else:
                        _size = 0
                    # 5) 请求下载
                    print('> 5 ', end='')
                    r = self.__get_Requests__(url)
                    t0 = time.time()
                    _size_chunk = 0
                    chunk_size = 1024*10
                    # 正式转发下载
                    print('>> %s(%s) --> %s(%s)' % (
                        _size, self.__getsize__(_size),
                        self._size_total, self.__getsize__(self._size_total)))
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        _size_chunk += len(chunk)
                        try:
                            self.__mysend__(chunk)
                        except Exception:
                            # print('详细错误信息:%s\n' % e, traceback.format_exc())
                            print('【发送失败】。。')
                            break
                    if (_size + int(_size_chunk)) >= int(self._size_total):
                        connfd.send('[ok]'.encode())
                        print('Success. 转发成功, ', end='')
                    else:
                        connfd.send(b'[FL]')
                        print('WARNING: 转发未成功, ', end='')
                    print('耗时%.3fs' % (time.time() - t0))
                    print('传输: %s(%s) --- [+ %s(%s)] ---> %s(%s)  all:%s(%s)' % (
                        _size,  self.__getsize__(_size),
                        _size_chunk,  self.__getsize__(_size_chunk),
                        _size + _size_chunk, self.__getsize__(
                            _size + _size_chunk),
                        self._size_total, self.__getsize__(self._size_total)))
                    connfd.close()
                    print('Connect closed\n')
                elif msg == b"[close]1234567":
                    try:
                        connfd.send(("[server has be closed.]").encode())
                        connfd.close()
                        print('服务端被终止\n')
                        break
                    except Exception as e:
                        print('发送[Download Failed]信号失败', e)
                else:
                    # with open('log-other', 'a', buffering=1) as fo:
                    print("\nConnect from", addr)
                    print(time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime()))
                    print('收到非指定信息：')
                    print(msg.strip())
                    text = 'Email: 1170101471@qq.com'
                    connfd.send(text.encode())
                    print('已发送：' + text)
                    print('Connect closed\n')
                    connfd.close()
            except KeyboardInterrupt:
                print('服务已终止!')
                break
            except socket.timeout:
                # print('经过了', time.time() - self.test_t0)
                pass
            except RequestErro as e:
                print('\n请求失败 MissingSchema:', e, '\n\n服务已重启')
            except Exception:
                # with open('log-conman', 'a', buffering=1) as fo:
                # print('额，遇到点问题，错误信息是:', e)#, file=fo)
                # try:
                #     connfd.send(("[Download Failed] %s" % str(e)).encode())
                #     connfd.close()
                # except Exception as e2:
                #     print('发送[Download Filed]失败', e2)#, file=fo)
                print('详细错误信息:\n', traceback.format_exc(), '\n服务已重启')
            finally:
                self._sock_s.close()
                if connfd:
                    connfd.close()
                time.sleep(1)


def main():
    args = fargv()
    pywgetServer().do_parent(args['proxy'])


if __name__ == "__main__":
    main()
