import os

import paramiko
import socket
import time

from qiniu import Auth, put_file, etag, CdnManager
import qiniu.config


hostname = "43.134.208.84"
username = "root"
password = ""
port = 2222

access_key = ''
secret_key = ''


def portstatus(hostname, port:int):
    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockobj.settimeout(3)
    if sockobj.connect_ex((hostname, port)) != 0:
        return 1
    return 0


def runcommand(hostname, username, password, port, cmd):
    with paramiko.SSHClient() as session:
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        session.connect(hostname=hostname, username=username, password=password, port=port)
        stdin, stdout, stderr = session.exec_command(cmd)
        print(stdout.readline())
        return stdin, stdout, stderr


def uploadqiniu():
    # 构建鉴权对象
    q = Auth(access_key, secret_key)

    # 要上传的空间
    bucket_name = 'service-pubic'

    # 上传后保存的文件名
    key = 'dao-vmess-node.yaml'

    token = q.upload_token(bucket_name, key, 3600)

    # 要上传文件的本地路径
    localfile = '/opt/config/dao-vmess-node.yaml'

    ret, info = put_file(token, key, localfile, version='v2')
    print(info)
    assert ret['key'] == key
    assert ret['hash'] == etag(localfile)


def flushcdn():
    auth = qiniu.Auth(access_key=access_key, secret_key=secret_key)
    cdn_manager = CdnManager(auth)

    # 需要刷新的文件链接
    urls = [
        'http://r0v6686yf.hb-bkt.clouddn.com/dao-vmess-node.yaml'
    ]

    # 刷新链接
    return cdn_manager.refresh_urls(urls)


def servicemonitor():
    oldport = 53
    while True:
        if portstatus(hostname, oldport) != 0:
            newport = oldport + 1
            # v2ray主机配置文件修改
            runcommand(hostname, username, password, port, F'''sed -e 's?port": {oldport}?port": {newport}?g' /etc/v2ray/config.json; v2ray.sh restart''')
            time.sleep(6)
            # 订阅文件端口修改
            status = os.system(F'''sed -e "s?port: {oldport}?port: {newport}?g" /opt/config/dao-vmess-node-test.yaml''')
            # 上传对象存储&刷新CDN
            uploadqiniu()
            flushcdn()

            oldport = newport
        time.sleep(30)


if __name__ == '__main__':
    servicemonitor()
