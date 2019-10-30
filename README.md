# pywget

### 简介：

* 用于下载文件的程序（支持断点续传）. (python)  Download file supports breakpoint resume. (python)
* 可以进行数据转发代理下载。

### 还需要改进的地方：

* 目前无法对ftp网址协议传输的文件进行下载及转发，日后需要跟进改进

### Example:

```bash
# sh run_server.sh  # 启动服务端
python3 proxy_wget_server.py  # 启动服务端

# sh run_client.sh  # 客户端通过代理运行示例（-p参数网址为服务端所在IP，如果公网IP可用，可以直接使用公网IP）
python3 pywget.py http://118.89.194.65/genome.gff3.idx -p 127.0.0.1:8080 -f

# sh run-test.sh    # 运行示例
python3 pywget.py http://118.89.194.65/genome.gff3.idx  # 下载指定网址名称
python3 pywget.py https://www.baidu.com                 # 下载百度首页
python3 pywget.py https://www.baidu.com -o test.html     # 自定义下载文件名
python3 pywget.py https://www.baidu.com -o test.html -f  # 当文件存在时强制覆盖
python3 pywget.py https://www.baidu.com -o test.html -f -p 127.0.0.1:8080  # 使用代理转发下载
```

