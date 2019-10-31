# -*- coding: utf-8 -*
# @Author: ChenJun
# @Email:  chenjun2049@foxmail.com
# @Qmail:  1170101471@qq.com
# @Date:   2019-09-08 17:24:02
# @Last Modified by:   JUN
# @Last Modified time: 2019-10-24 20:08:12

import os,sys
import argparse
import datetime,time
import requests
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

    def __support_continue_do__(self, stat):
        '''升级self.headers'''
        local_filename, tmp_filename = self.local_filename, self.tmp_filename
        if stat:  # 支持断点续传
            print('[stat]支持断点续传')
            if not os.path.exists(tmp_filename):
                self.__touch__(local_filename)
                self.__touch__(tmp_filename)
        else:
            print('[stat]下载不支持断点续传，已重置下载文件')
            self.__touch__(local_filename)
            self.__touch__(tmp_filename)
        if self._size != 0:
            headers_range = "bytes=%d-" % (self._size - 1)
            # headers_range = "bytes=%d-" % (self._size if self._size == 0
            #                                else self._size - 1)
            self._headers.update(headers_range)

    def download(self):
        '''主程序'''
        # 1) 文件准备
        finished = False
        print('Download start:')
        print('[url]:', self._url)
        url, filename, force, block = self._url, self.filename, self.force, self._block
        if not filename:
            filename = self.__remove_nonchars__(url.split('/')[-1].split('?')[0])
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
                except Exception:
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
                self.__touch__(tmp_filename)
        else:  # 否则重建文件
            self.__touch__(local_filename)
            self.__touch__(tmp_filename)

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
        except KeyboardInterrupt:
            print('\n程序终止')
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
