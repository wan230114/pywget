- 需要将iter进行统一，将请求发送报头的全过程融合进入信息转发传递前。
  - 已解决


- 当多次使用代理时，会莫名其妙第一次传输上一次的内容，第一次的直接被遗失掉了。想不通原因是什么。
  - 原因已查明，是由于 headers 变量未定义到类属性，造成下次开始前 headers 仍然使用的上次的。


- 2020-04-20周一22:55
- 思考发送一个文件真的需要打包吗？这个过程是否造成了传输速度的缓慢？


- 为何子进程在Window下开启失败，而在Linux下则成功运行？


- 2020-04-21周二11:00 获取长度的BUG问题发现。

python3 pywget.py https://www.arabidopsis.org/download_files/Genes/Araport11_genome_release/Araport11_blastsets/Araport11_genes.201606.pep.fasta.gz -f -p 144.34.179.134:8080 -c

已修复。在continue测试中修改为__get_request__中添加多层跳转请求

- 2020-04-22周三18:10 修复子进程一直运行的BUG

在断点续传中，由于传输时间过短，造成子进程中判断下载还没开始，导致无限死循环。

解决方案，将开始信息写入共享内存。