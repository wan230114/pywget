# -*- coding: utf-8 -*-
# @Author: ChenJun
# @Email:  chenjun4663@novogene.com
# @Qmail:  1170101471@qq.com
# @Date:   2019-06-23 00:27:09
# @Last Modified by:   11701
# @Last Modified time: 2019-09-11 23:40:35

from socket import *
# from urllib.request import urlopen
import time
import traceback
import re
import struct
import json
import requests
import sys


print0 = print


def print(*args, **kwargs):
    kwargs.update({'flush': True})
    print0(*args, **kwargs)


class pywgetServer:

    def __touch__(self, filename):
        '''clean file'''
        with open(filename, 'w+') as fin:
            print('touch_file:', filename)

    def __init__(self, proxy):
        self._sock_s = self.__getsocket__(proxy)

    def __getsocket__(self, proxy):
        '''创建套接字，创建链接，创建父子进程　功能函数调用'''
        HOST, PORT = proxy.split(':')
        ADDR = (HOST, int(PORT))
        # ADDR = ('0.0.0.0', 8080)  # server address
        # 创建tcp套接字
        s = socket(AF_INET, SOCK_STREAM)
        # 在绑定前调用setsockopt让套接字允许地址重用
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # 绑定
        s.bind(ADDR)
        # 设置监听
        s.listen(5)
        return s

    def __support_continue__(self, url):
        '''test url'''
        headers = {
            'Range': 'bytes=0-'
        }
        try:
            r = requests.head(url, headers=headers)
            crange = r.headers['content-range']
            self._size_totol = int(re.match(r'^bytes 0-\d+/(\d+)$', crange).group(1))
            print('下载支持断点续传')
            return 1, self._size_totol
        except Exception:
            try:
                self._size_totol = int(r.headers['content-length'])
            except Exception:
                self._size_totol = 0
            print('下载不支持断点续传')
            return 0, self._size_totol

    def __recv_size__(self, len_s):
        '''处理tcp的收发缓冲区导致的接受不完全问题'''
        s = self._sock_c
        # print('01start', len_s)
        L = []
        all_size = 0
        while all_size < len_s:
            size = len_s - all_size
            # print('will-->', size)
            msg = s.recv(size)
            if not msg:
                break
            all_size += len(msg)
            L.append(msg)
        # print('\n---------------\n', b''.join(L), '\n------------\n')
        assert all_size == len_s, "getsize != len_s, %s/%s" % (all_size, len_s)
        return b''.join(L)

    def __myrecv__(self):
        '''获取固定报头信息'''
        ll = self.__recv_size__(4)  # 1.获取报头
        header_size = struct.unpack('i', ll)[0]  # 2.解析报头
        header_json = self.__recv_size__(header_size).decode('utf-8')  # 3.接收报文
        header_dic = json.loads(header_json)  # 4.解析报文
        size = header_dic['size']  # 5.获取真实数据的长度
        return self.__recv_size__(size)

    def __mysend__(self, msg):
        '''发送带报头信息的信息'''
        s = self._sock_c
        header_dic = {'size': len(msg)}  # 1.包装报文
        header_json = json.dumps(header_dic).encode('utf-8')  # 2.处理报文
        s.send(struct.pack('i', len(header_json)))  # 3.发送报头
        s.send(header_json)  # 4.发送报文
        s.send(msg)  # 5.发送真实的数据

    def do_parent(self):
        while True:
            try:
                connfd, addr = self._sock_s.accept()
                self._sock_c = connfd
                # 0) 接收请求
                msg = connfd.recv(10)
                if msg.startswith(b'[send-url]'):
                    # 0) 接收url请求
                    msg = self.__myrecv__().decode()  # 接收url
                    print("\nConnect from", addr)  # , file=fo)
                    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))  # , file=fo)
                    url, who = re.findall(r'\[send-url\](.*)\[(.*)\]', msg)[0]
                    print('收到url请求: ', msg, '\n转发中:', url, who)  # , file=fo)

                    # 1) 发送是否可以续传和开始信息
                    stat, total_size = self.__support_continue__(url)
                    print(stat, total_size)
                    connfd.send(('%s[start]' % stat).encode('utf-8'))

                    # 2) 接收网页请求头
                    headers = json.loads(self.__myrecv__())
                    size = int(re.findall('bytes=(\d*)-', headers['Range'])[0])

                    # 3) 发送下载文件长度
                    self.__mysend__(str(self._size_totol).encode('utf-8'))

                    # 4) 请求下载
                    r = requests.get(url, stream=True, headers=headers)

                    t0 = time.time()
                    allsize = 0
                    chunk_size = 1024*100
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        allsize += len(chunk)
                        try:
                            self.__mysend__(chunk)
                        except Exception as e:
                            print('【发送失败】。。')
                            print('详细错误信息:%s\n' % e,
                                  traceback.format_exc())  # , file=fo)
                            # try:
                            #     connfd.send(
                            #         ("[Download Failed]" % str(e)).encode())
                            # except Exception:
                            #     print('send [Download Failed] failed')#, file=fo)
                            break
                    # print(allsize, total_size)
                    if (size + int(allsize)) == int(total_size):
                        print('sending [ok]...')  # , file=fo)
                        connfd.send('[ok]'.encode())
                        print('sened[ok],耗时%.3fs,传输%s/%s' % (
                              (time.time() - t0), allsize, total_size))  # , file=fo)
                        print('Success. 转发成功')  # , file=fo)
                    else:
                        connfd.send(b'[FL]')
                        print('WARNING: 转发未成功')  # , file=fo)
                    connfd.close()
                    print('Connect closed\n')  # , file=fo)
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
                    print("\nConnect from", addr)  # , file=fo)
                    print(time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime()))  # , file=fo)
                    print('收到非指定信息：')  # , file=fo)
                    print(msg.strip())  # , file=fo)
                    text = 'Email: 1170101471@qq.com'
                    connfd.send(text.encode())
                    print('已发送：' + text)  # , file=fo)
                    print('Connect closed\n')  # , file=fo)
                    connfd.close()

            except KeyboardInterrupt:
                print('服务已终止!')
                self._sock_s.close()
                break
            except Exception as e:
                # with open('log-conman', 'a', buffering=1) as fo:
                # print('额，遇到点问题，错误信息是:', e)#, file=fo)
                # try:
                #     connfd.send(("[Download Failed] %s" % str(e)).encode())
                #     connfd.close()
                # except Exception as e2:
                #     print('发送[Download Filed]失败', e2)#, file=fo)
                print('详细错误信息:\n', traceback.format_exc(), '\n服务已重启')  # , file=fo)
            finally:
                connfd.close()


def main():
    try:
        proxy = sys.argv[1]
    except:
        proxy = '0.0.0.0:8080'

    pywgetServer(proxy).do_parent()


if __name__ == "__main__":
    main()
