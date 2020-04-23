ps xjf |grep proxy_wget_server.py|grep -v grep|awk '{print $2}'|xargs kill 2>/dev/null
sleep 1
nohup python3 proxy_pywget_server.py &>log &
