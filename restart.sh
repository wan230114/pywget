ps xjf |grep proxy_pywget_server.py|grep -v grep|awk '{print $2}'|xargs kill 2>/dev/null
sleep 1
times=`date "+.%F_%H.%M.%S"`
nohup python3 proxy_pywget_server.py 1>log${times} 2>log${times}-other &
