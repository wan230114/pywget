# -*- coding: utf-8 -*-
# @Author: ChenJun
# @Email:  chenjun2049@foxmail.com
# @Qmail:  1170101471@qq.com
# @Date:   2019-09-08 02:55:15
# @Last Modified by:   JUN
# @Last Modified time: 2019-09-08 13:29:56

import requests
import sys
import os
import re
import time
import argparse


def fargv():
    parser = argparse.ArgumentParser(description='用于下载文件的程序.')
    parser.add_argument('url', type=str,
                        help='输入需要下载的文件网址')
    parser.add_argument('-o', '--filename', type=str, default=0,
                        help='输出文件的name')
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='当下载文件存在时是否跳过询问直接覆盖')
    args = parser.parse_args()
    return args


class pywget:
    '''download file function'''

    def __init__(self, config={}):
        self.config = {'block': int(config['block'] if 'block' in config else 1024)}
        self.total = 0
        self.size = 0
        self.filename = ''

    def download(self, url, filename, force):
        '''主程序'''
        # 1) 文件准备
        finished = False
        size = self.size
        block = self.config['block']
        headers = {"User-Agent": "Wget/1.12 (cygwin)", "Accept": "*/*"}
        if not filename:
            filename = self.__remove_nonchars__(url.split('/')[-1])
        local_filename = self.__remove_nonchars__(filename)
        tmp_filename = local_filename + '.downtmp'
        if os.path.exists(local_filename) and not os.path.exists(tmp_filename):
            print('下载文件已存在，%s' % local_filename)
            if not force:
                if input('是否覆盖文件？(回车-->覆盖，任意字符串退出)'):
                    sys.exit(1)
            self.__touch__(local_filename)
        if self.__support_continue__(url):  # 支持断点续传
            try:
                with open(tmp_filename, 'rb') as fin:
                    self.size = int(fin.read())
                    size = self.size
            except Exception:
                self.__touch__(tmp_filename)
            finally:
                headers['Range'] = "bytes=%d-" % (self.size if self.size == 0 else self.size - 1)
        else:
            self.__touch__(tmp_filename)
            self.__touch__(local_filename)

        # 2) 请求开始
        total = self.total
        r = requests.get(url, stream=True, verify=False, headers=headers)

        start_t = time.time()
        if total > 0:
            print("[+] Size: %s" % self.__getsize__(total - size))
        else:
            print("[+] Size: None")
        print("Downloading...")
        try:
            with open(local_filename, 'ab+') as f:
                f.seek(self.size if self.size == 0 else self.size - 1)
                f.truncate()
                n = 0.1
                for chunk in r.iter_content(chunk_size=block):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        size += len(chunk)
                        try:
                            if size / total > n:
                                n += 0.1
                                sys.stdout.write('Now: %s, Total: %s\n' %
                                                 (self.__getsize__(size),
                                                  self.__getsize__(total)))
                                sys.stdout.flush()
                        except ZeroDivisionError:
                            pass
                finished = True
                os.remove(tmp_filename)
                spend = time.time() - start_t
                speed_tmp = self.__getsize__(size - self.size)
                speed = float(speed_tmp[:-1]) / spend
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
                    ftmp.write(str(size))

    def __remove_nonchars__(self, name):
        '''clean name'''
        newname, n = re.subn(r'[\\\/\:\*\?\"\<\>\|]', '', name)
        if n:
            print('file renamed: %s --> %s' % (name, newname))
        return name

    def __touch__(self, filename):
        '''clean file'''
        with open(filename, 'w+') as fin:
            pass

    def __support_continue__(self, url):
        '''test url'''
        headers = {
            'Range': 'bytes=0-'
        }
        try:
            r = requests.head(url, headers=headers)
            crange = r.headers['content-range']
            self.total = int(re.match(r'^bytes 0-\d+/(\d+)$', crange).group(1))
            print('下载支持断点续传')
            return True
        except Exception:
            pass
        try:
            self.total = int(r.headers['content-length'])
        except Exception:
            self.total = 0
        print('下载不支持断点续传')
        return False

    def __getsize__(self, size):
        '''get size'''
        D = {0: 'B', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        for x in D:
            if int(size) < 1024**(x + 1):
                hsize = str('%.3f' % (int(size) / 1024**x)) + D[x]
                return hsize


if __name__ == '__main__':
    kwargs = fargv()
    # url = 'http://118.89.194.65/genome.gff3.idx'
    pywget().download(kwargs.url, kwargs.filename, kwargs.force)
