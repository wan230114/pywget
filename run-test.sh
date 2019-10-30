# sh run-test.sh    # 运行示例
python3 pywget.py http://118.89.194.65/genome.gff3.idx  # 下载指定网址名称
python3 pywget.py https://www.baidu.com                 # 下载百度首页
python3 pywget.py https://www.baidu.com -o test.html     # 自定义下载文件名
python3 pywget.py https://www.baidu.com -o test.html -f  # 当文件存在时强制覆盖
python3 pywget.py https://www.baidu.com -o test.html -f -p 127.0.0.1:8080  # 使用代理转发下载
