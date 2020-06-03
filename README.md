# pywget

### 简介：

* 用于下载文件的程序（支持断点续传）. (python)  Download file supports breakpoint resume. (python)
* 可以进行数据转发代理下载。

### 使用方法

```bash
git clone https://github.com/wan230114/pywget.git
```

### 提升空间：

* 目前无法对ftp网址协议传输的文件进行下载及转发，日后需要跟进改进
* 自动断点续传会概率性出现：客户端接收先于服务端就绪状况而导致报错退出，可以尝试修复一下使代码更为健壮。
* 打印日志优化，下载完成后末尾分隔开来，多一行换行。

### Example:

（服务端与客户端可在两台计算机分别运行）

运行示例：
```bash

# 1) 本地下载
python3 pywget.py http://118.89.194.65/genome.gff3.idx
# 下载指定网址名称，自动命令
python3 pywget.py https://www.baidu.com
# 下载百度首页，命名为test_baidu.html
python3 pywget.py https://www.baidu.com -o test_baidu.html
# 当文件存在时强制覆盖
python3 pywget.py https://www.baidu.com -o test_baidu.html -f

# 2) 使用代理转发下载，需要提前运行服务端
# 客户端通过代理运行示例（-p参数网址为服务端所在IP）
# 如果公网IP可用，可以改掉127.0.0.1直接使用运行服务端的公网IP
python3 pywget.py http://118.89.194.65/genome.gff3.idx -p 127.0.0.1:8080 -f
python3 pywget.py https://www.baidu.com -o test_baidu.html -f -p 127.0.0.1:8080
```

服务端的运行：
```bash
python3 ./proxy_pywget_server.py
```
