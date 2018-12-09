all:
	git pull origin master
	git push
	echo $${token}
	ssh root@37.139.30.202 "cd /var/www/uiguy.ru/oil-stone-urban-hackaton/repo && git pull && token=$${token} make restart"

deploy: all

restart:
	echo RESTART
	echo $${token}
	pwd
	kill -15 $$(cat ./pid); token=$${token} make start

start:
	echo START
	echo $${token}
	tmux new -d './index.py $${token} >log 2>error_log'
