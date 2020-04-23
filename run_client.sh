# 运行示例

# 1) 本地下载
python3 pywget.py http://118.89.194.65/genome.gff3.idx
# 下载指定网址名称，自动命令
python3 pywget.py https://www.baidu.com
# 下载百度首页，命名为test_baidu.html
python3 pywget.py https://www.baidu.com -o test_baidu.html
# 当文件存在时强制覆盖
python3 pywget.py https://www.baidu.com -o test_baidu.html -f

# 2) 使用代理转发下载，需要提前运行服务端
# 客户端通过代理运行示例（-p参数网址为服务端所在IP，如果公网IP可用，可以直接使用公网IP）
python3 pywget.py http://118.89.194.65/genome.gff3.idx -p 127.0.0.1:8080 -f
python3 pywget.py https://www.baidu.com -o test_baidu.html -f -p 127.0.0.1:8080
python3 pywget.py https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -f -p 144.34.179.134:8080

# 测试多层跳转
python3 pywget.py https://www.arabidopsis.org/download_files/Genes/Araport11_genome_release/Araport11_blastsets/Araport11_genes.201606.pep.fasta.gz -f
python3 pywget.py https://www.arabidopsis.org/download_files/Microarrays/Affymetrix/affy_AG_array_elements-2010-12-20.txt -f