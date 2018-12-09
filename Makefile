all:
	git pull origin master
	git push
	ssh root@37.139.30.202 'cd /var/www/uiguy.ru/oil-stone-urban-hackaton/repo && git pull && make restart'

deploy: all

restart:
	kill -15 $(cat ./pid) && make start

start:
	python3 index.py
