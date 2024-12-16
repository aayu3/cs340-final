.PHONY: start test background stop

start:
	python3 hub.py &
	python3 newdomain.py

background:
	nohup python3 newdomain.py </dev/null >>log1 2>>log2 &

stop:
	killall -SIGINT python3


test:
	python3 -m pytest
