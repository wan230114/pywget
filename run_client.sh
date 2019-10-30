# sh run_client.sh  # 客户端通过代理运行示例（-p参数网址为服务端所在IP，如果公网IP可用，可以直接使用公网IP）
python3 pywget.py http://118.89.194.65/genome.gff3.idx -p 127.0.0.1:8080 -f