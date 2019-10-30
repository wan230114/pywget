'''
存储基本功能的模块
'''
import re
import os


class pywget_funcs:
    '''
    base
    '''
    def __init__(self, config={}):
        self._url = config['url']
        self.filename = config.get('filename', None)
        self.force = config.get('force', False)
        self._speed_end = '\n' if config.get('complete', False) else '\r'
        self._block = int(config.get('block', 1024))
        self._headers = config.get(
            'headers', {"User-Agent": "Wget/1.12 (cygwin)", "Accept": "*/*"})
        self._proxy = config.get('proxy', None)
        self._sock = self.__server_Connect__(
            self._proxy) if self._proxy else False
        self._size = 0  # 记录断点位置字节数
        self._size2 = 0  # 记录此时获得了多少字节数据
        self._size_recved = 0  # 接收的字节数
        self._size_total = 0  # 需要下载的文件总字节数

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
            self.__touch__(local_filename)
            self.__touch__(tmp_filename)
        if self._size != 0:
            headers_range = "bytes=%d-" % (self._size - 1)
            # headers_range = "bytes=%d-" % (self._size if self._size == 0
            #                                else self._size - 1)
            self._headers.update(headers_range)
