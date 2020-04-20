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
from packages.pywget_funcs import pywget_funcs

print0 = print


def print(*args, **kwargs):
    kwargs.update({'flush': True})
    print0(*args, **kwargs)


class pywgetServer(pywget_funcs):

    def __getsocket__(self, proxy):
        '''创建套接字，创建链接，创建父子进程　功能函数调用'''
        HOST, PORT = proxy.split(':')
        ADDR = (HOST, int(PORT))
        # ADDR = ('0.0.0.0', 8080)  # server address
        # 创建tcp套接字
        s = socket(AF_INET, SOCK_STREAM)
        # 在绑定前调用setsockopt让套接字允许地址重用
        # s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # 绑定
        s.bind(ADDR)
        # 设置监听
        s.listen(5)
        return s

    def do_parent(self, proxy):
        self._sock_s = self.__getsocket__(proxy)
        while True:
            try:
                self._size_NOW = 0
                connfd, addr = self._sock_s.accept()
                self._sock = connfd
                # 0) 接收请求
                msg = connfd.recv(10)
                if msg.startswith(b'[send-url]'):
                    # 0) 接收url请求
                    msg = self.__myrecv__().decode()  # 接收url
                    print("\nConnect from", addr)
                    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                    url, who = re.findall(r'\[send-url\](.*)\[(.*)\]', msg)[0]
                    print('收到url请求: ', msg, '\n转发中:', url, who)

                    # 1) 发送是否可以续传和开始信息
                    stat = self.__support_continue__(url)
                    total_size = self._size_total
                    connfd.send(('%s[start]' % stat).encode('utf-8'))

                    # 2) 接收网页请求头
                    self._headers = json.loads(self.__myrecv__())
                    if stat and self._headers.get('Range', 0):
                        # 此时传输大小size
                        size = int(re.findall(
                            'bytes=(\d*)-', self._headers['Range'])[0])
                    else:
                        size = 0

                    # 3) 发送下载文件长度
                    self.__mysend__(str(self._size_total).encode('utf-8'))

                    # 4) 请求下载
                    # r = requests.get(url, stream=True, headers=headers)
                    r = self.__get_Requests__(url)
                    t0 = time.time()
                    allsize = 0
                    chunk_size = 1024*100
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        allsize += len(chunk)
                        try:
                            self.__mysend__(chunk)
                            # print('发送：---->\n', chunk[:30], flush=True, file=sys.stderr)
                        except Exception as e:
                            print('【发送失败】。。')
                            print('详细错误信息:%s\n' % e,
                                  traceback.format_exc())
                            # try:
                            #     connfd.send(
                            #         ("[Download Failed]" % str(e)).encode())
                            # except Exception:
                            #     print('send [Download Failed] failed')#, file=fo)
                            break
                    if (size + int(allsize)) >= int(total_size):
                        # print('sending [ok]...')
                        connfd.send('[ok]'.encode())
                        print('sened[ok],耗时%.3fs,传输%s/%s' % (
                            (time.time() - t0), allsize, total_size))
                        print('Success. 转发成功, ', end='')
                    else:
                        connfd.send(b'[FL]')
                        print('WARNING: 转发未成功, ', end='')
                    print('传输: %s --- [+ %s] ---> %s / %s' % (
                        size, allsize, size + int(allsize), int(total_size)))
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
            except Exception as e:
                # with open('log-conman', 'a', buffering=1) as fo:
                # print('额，遇到点问题，错误信息是:', e)#, file=fo)
                # try:
                #     connfd.send(("[Download Failed] %s" % str(e)).encode())
                #     connfd.close()
                # except Exception as e2:
                #     print('发送[Download Filed]失败', e2)#, file=fo)
                print('详细错误信息:\n', traceback.format_exc(), '\n服务已重启')
                time.sleep(2)
            finally:
                connfd.close()


def main():
    try:
        proxy = sys.argv[1]
    except:
        proxy = '0.0.0.0:8080'

    pywgetServer().do_parent(proxy)


if __name__ == "__main__":
    main()
