#!/bin/sh
if test "$1" = "local"; then
	echo "ローカル開発サーバへのインポートを行います"
	server="localhost:12080"
elif test "$1" = "test"; then
	echo "開発・検証サーバへのインポートを行います"
	server="plumplan-dev.appspot.com"
elif test "$1" = "honban"; then
	echo "本番サーバへのインポートを行います"
	server="plumplan-agri.appspot.com"
else
	echo "USAGE: ./upload_data.sh [local | test | honban] csvファイル名 kind名"
	echo "第一引数には、local / test / honban のいずれかを指定してください"
	echo "第二引数には、アップロードするCSVファイル名を指定してください"
	echo "第三引数には、アップロード先のカインド名を指定してください"
	exit 0
fi
appcfg.py upload_data --config_file=../agrimarket/bulkloader.yaml --email=agriadmin@www.jsol.co.jp --filename=$2 --kind=$3 --url=http://$server/_ah/remote_api
