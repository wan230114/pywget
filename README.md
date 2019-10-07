# pywget

### 版本：

* v2.0 加入代理转发功能，发布客户端与服务端
* v1.0 实现基本下载文件的功能。

### 简介：

* 用于下载文件的程序（支持断点续传）. (python)  Download file supports breakpoint resume. (python)
* 可以进行数据转发代理下载。

### 还需要改进的地方：

* 目前无法对ftp协议传输的文件进行下载及转发，日后需要跟进改进

### Example:

```bash
sh run_server.sh  # 启动服务端
sh run_client.sh  # 客户端运行示例
sh run-test.sh    # 客户端运行示例
```
