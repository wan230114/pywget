#!/usr/bin/env python3
# -*- coding:utf-8 -*-

#############################################
# @ Author: Chen Jun
# @ Author Email: 1170101471@qq.com
# @ Created Date: 2019-09-08 17:24:02
# @ Modified By: Chen Jun
# @ Last Modified: 2021-08-03, 19:12:22
#############################################


import os
import re
import sys
import argparse
import datetime
import time
from packages.pywget_funcs import pywget_funcs, RequestErro
from multiprocessing import Process, Array


def fargv():
    parser = argparse.ArgumentParser(description='用于下载文件的程序.')
    parser.add_argument('url', type=str,
                        help='输入需要下载的文件网址')
    parser.add_argument('-o', '--filename', type=str, default=None,
                        help='输出的下载文件的name')
    parser.add_argument('-p', '--proxy', type=str, default=None,
                        help='代理服务端的IP及端口，如：118.96.72.54:8668')
    parser.add_argument('-t', '--RetryTime', type=int, default=1000,
                        help='是否重试无限次，默认1000次，输入0代表无限次')
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='是否强制覆盖已下载文件')
    parser.add_argument('-c', '--complete', action='store_true', default=False,
                        help='是否完整打印日志')
    args = parser.parse_args()
    print(args)
    return args.__dict__


class pywget(pywget_funcs):
    '''download file function'''

    def __init__(self, config={}):
        super().__init__(config=config)
        self.finished = False
        self._size_NOW = self._size  # 记录此时获得了多少数据
        # 创建共享内存，[开始, 结束, 计算速度, 存储当前大小]
        self._shm = Array('l', [0, 0, 0, self._size_NOW, self._size_total])

    def jg_isexits(self):
        """通过标准输入来判断是否覆盖原文件"""
        for x in range(3):
            a = input('检测本地文件与待下载文件大小一致，是否覆盖原文件？[y|n]\n[n] >>> ')
            if a == "y":
                return True
            elif not a or a == "n":
                return False
            print(' (请输入y/n, 或直接按回车默认输入n)')

    def show_speed(self):
        """使用子进程显示下载速度"""
        # print('开启子进程')
        try:
            _size2_last = list(self._shm)[2]
            flush_speed = 1
            while True:
                start, end, isrun, _size_NOW, _size_total = self._shm
                if end:
                    break
                if start and isrun:
                    speed = (_size_NOW - _size2_last) / flush_speed
                    if speed > 0 and _size_total > 0:
                        seconds = datetime.timedelta(
                            seconds=(_size_total - _size_NOW) / speed)
                    else:
                        seconds = '-:--:--.------'
                    sys.stdout.write(
                        'Now: %8s, Download Speed: %8s/s  in %s  NowTime:%s  %s' % (
                            self.__getsize__(_size_NOW),
                            self.__getsize__(speed),
                            seconds,
                            str(datetime.datetime.now())[11:-7],
                            self._speed_end))
                    sys.stdout.flush()
                    _size2_last = _size_NOW
                time.sleep(flush_speed)
        except KeyboardInterrupt:
            print('')  # 终止时加一个\n
        # print('关闭子进程')

    def __deal_file__(self):
        """
        查看文件是否之前已经下载完毕
        指标1：缓存文件不存在
        指标2：大小一致
        """
        if not self.force and os.path.exists(self.local_filename):
            # 不强制覆盖，下载文件存在
            local_filename_size = os.path.getsize(self.local_filename)
            if local_filename_size == self._size_total:
                self.finished = True
                if not self.jg_isexits():
                    # 大小一致，并且不覆盖文件
                    print('下载文件已存在: %s' % self.local_filename)
                    print('文件字节数:', self._size_total,
                          self.__getsize__(self._size_total))
                    print('已跳过下载')
                    return 1
            elif self._stat:
                # 支持断点续传
                self._size = self._size_NOW = local_filename_size
                if not os.path.exists(self.tmp_filename):
                    print('\n[WARNING]: 缓存文件不存在, 断点续传结束后请检查下载的文件完整性\n')
                    self.__touch__(self.tmp_filename)
                return 0
            # elif (local_filename_size > 0) and \
            #     (local_filename_size == self._size_total or
            #         self._size_total == 0):
        self.__touch__(self.local_filename)
        self.__touch__(self.tmp_filename)
        return 0

    def __getIter__(self, size):
        if not self._is_sock:
            self.__support_continue_do__(self._stat, size)  # 升级headers
            r = self.__get_Requests__(self._url)
            print('最终请求网址：', r.url)
            return r.iter_content(chunk_size=self._block)
        else:
            return self.__recv_data__()

    def download(self):
        '''主程序'''
        print('Download start:')
        print('[url]:', self._url)
        # 0) header请求
        r = self.__get_Requests__(self._url, headers=self._headers_copy)
        tmpname = re.findall("filename=\"(.*?)\";",
                             r.headers.get("Content-Disposition", ""))
        if tmpname and not self.filename:
            self.filename = tmpname[0]

        # 1) 文件名准备
        if not self.filename:
            self.filename = self.__remove_nonchars__(
                self._url.split('/')[-1].split('?')[0])
        self.local_filename = self.__remove_nonchars__(self.filename)
        self.tmp_filename = self.local_filename + '.downtmp'

        # 执行下载开始
        self._RetryTime_tmp = self._RetryTime if self._RetryTime else -1
        self._RetryTime_tmp2 = self._RetryTime_tmp

        p = Process(target=self.show_speed)
        p.start()
        self.download_start()
        p.join()

    def download_start(self, checkfile=1):
        try:
            self._shm[0] = 0
            # 1) 请求开始前，准备工作，获取是否支持断点续传信息，获取长度信息
            if not self._is_sock:
                self._stat = self.__support_continue__(self._url)
            else:
                i = 0
                while True:
                    i += 1
                    if self._RetryTime_tmp2 == 0:
                        print('连接出错!')
                        raise
                    elif self._RetryTime_tmp2 > 0:
                        self._RetryTime_tmp2 -= 1
                        i_msg = '正在重新连接，第%d(%s)次' % (i, self._RetryTime)
                    else:
                        i_msg = '正在重新连接，第%d次' % i
                    try:
                        time.sleep(0.2)
                        self._sock = self.__s_Connect__(self._proxy)
                        self.__do_recv__()
                    except ConnectionResetError:
                        print('连接超时, %s' % i_msg)
                    except ConnectionRefusedError:
                        print('连接出错, %s' % i_msg)
                    except AssertionError:
                        print('接收失败, %s' % i_msg)
                    else:
                        break
                    finally:
                        time.sleep(2)
            if self._stat:  # 支持断点续传
                print('[stat]支持断点续传')
            else:
                print('[stat]下载不支持断点续传')
            self._shm[4] = self._size_total
            # 2) 看文件是否已经下载完成（是否需要断点续传）
            if checkfile:
                if self.__deal_file__():
                    self.finished = True
                    return
                else:
                    self._size_NOW = self._size
            self.__support_continue_do__(self._stat, self._size_NOW)
            # 3) 获取请求数据的迭代对象
            self._iters = self.__getIter__(self._size_NOW)
            print("Downloading...")
            if self._size_total > 0:
                size_need = self._size_total - self._size_NOW
                print('[Size]:', self._size_NOW,
                      '-- [+%d] --> %d(%s)' % (
                          size_need, self._size_total,
                          self.__getsize__(self._size_total)))
            else:
                print("[Size]: None")
            _size_NOW_copy = self._size_NOW
            with open(self.local_filename, 'ab+', buffering=0) as f:
                time_start = datetime.datetime.now()
                self._shm[0] = 1
                for chunk in self._iters:
                    if chunk:
                        f.write(chunk)
                        self._size_NOW += len(chunk)
                        self._shm[2], self._shm[3] = 1, self._size_NOW
                # input()
                # if self.__tmp__ == 0:
                #     sys.exit()
                # else:
                #     self.__tmp__ += 1
            if self._size_total <= self._size_NOW:
                self.finished = True
                if self._size_total == 0:
                    print('WARNING, 由于请求下载的字节数未知，请核对下载文件是否完整')
                elif os.path.exists(self.tmp_filename):
                    os.remove(self.tmp_filename)
                time_spend = datetime.datetime.now() - time_start
                speed_tmp = self.__getsize__(
                    self._size_NOW - _size_NOW_copy)
                speed = float(speed_tmp[:-1]) / (
                    time_spend.total_seconds() if time_spend.total_seconds() else 1)
                sys.stdout.write(
                    '[Download Finished]!\n[Total Time]: '
                    '%s\n[Download Speed]: %.3f %sb/s\n' % (
                        time_spend, speed, speed_tmp[-1]))
                sys.stdout.flush()
                if self._size_NOW > self._size_total:
                    print('WARNING, 下载可能有问题  ', end='')
                if self._size_total:
                    comp_ = ' %.3f%%' % (self._size_NOW/self._size_total*100)
                else:
                    comp_ = ''
                print('已下载(b)/总字节数(b)：', self._size_NOW,
                      '/', self._size_total, comp_)
            elif self._stat:  # 重试连接
                time.sleep(1)
                if self._RetryTime == 0:
                    self._RetryTime_tmp += 1
                    self.download_start(0)
                    print('\n\n下载中断，正在断点续传，正在进行第%d次重试' % self._RetryTime_tmp)
                elif self._RetryTime_tmp > 0:
                    self._RetryTime_tmp -= 1
                    print('\n\n下载中断，正在断点续传，正在进行第%d(%d)次重试' % (
                        self._RetryTime - self._RetryTime_tmp,
                        self._RetryTime))
                    self.download_start(0)
                else:
                    print('已达到重试次数：', self._RetryTime)
        except KeyboardInterrupt:
            print('\n\n程序终止')
        except RequestErro as e:
            print('请求失败')
            print('MissingSchema:', e)
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            self._shm[1] = 1


def main():
    # 创建共享内存，存入列表　
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
