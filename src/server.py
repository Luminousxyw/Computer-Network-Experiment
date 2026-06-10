import socket
import threading
import json
import os
from datetime import datetime

HOST = '127.0.0.1'
PORT = 12345

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'out', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
USER_DB_FILE = os.path.join(DATA_DIR, 'users.json')

online_users = {}
lock = threading.RLock()

def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def recv_msg(sock):
    raw_len = sock.recv(4)
    if not raw_len:
        return None
    length = int.from_bytes(raw_len, 'big')
    data = b''
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            return None
        data += chunk
    return json.loads(data.decode('utf-8'))

def send_msg(sock, msg_dict):
    data = json.dumps(msg_dict, ensure_ascii=False).encode('utf-8')
    length = len(data)
    sock.sendall(length.to_bytes(4, 'big') + data)

def broadcast_online(username):
    msg = {'type': 'response', 'content': f'{username} 上线了'}
    with lock:
        for u, s in online_users.items():
            if u != username:
                try:
                    send_msg(s, msg)
                except:
                    pass

def broadcast_offline(username):
    msg = {'type': 'response', 'content': f'{username} 下线了'}
    with lock:
        for u, s in online_users.items():
            if u != username:
                try:
                    send_msg(s, msg)
                except:
                    pass

def send_online_list(conn):
    with lock:
        names = list(online_users.keys())
    msg = {
        'type': 'response',
        'content': '在线用户：' + ', '.join(names) if names else '当前无人在线'
    }
    send_msg(conn, msg)

def forward_private(msg):
    sender = msg['sender']
    receiver = msg['receiver']
    with lock:
        if receiver in online_users:
            try:
                send_msg(online_users[receiver], msg)
                return
            except:
                pass
    sender_sock = online_users.get(sender)
    if sender_sock:
        err = {'type': 'response', 'content': f'用户 {receiver} 不在线'}
        send_msg(sender_sock, err)

def broadcast_group(msg):
    sender = msg['sender']
    with lock:
        for u, s in online_users.items():
            if u != sender:
                try:
                    send_msg(s, msg)
                except:
                    pass

def handle_client(conn, addr):
    username = None
    try:
        while True:
            msg = recv_msg(conn)
            if not msg:
                break
            msg_type = msg.get('type')
            if msg_type == 'register':
                users = load_users()
                new_user = msg['sender']
                password = msg['password']
                if not new_user or not password:
                    send_msg(conn, {'type': 'response', 'content': '用户名和密码不能为空'})
                elif new_user in users:
                    send_msg(conn, {'type': 'response', 'content': '用户名已存在'})
                else:
                    users[new_user] = password
                    save_users(users)
                    send_msg(conn, {'type': 'response', 'content': '注册成功，请登录'})
            elif msg_type == 'login':
                users = load_users()
                user = msg['sender']
                pwd = msg['password']
                if user in users and users[user] == pwd:
                    with lock:
                        if user in online_users:
                            send_msg(conn, {'type': 'response', 'content': '该账号已在线，请勿重复登录'})
                        else:
                            online_users[user] = conn
                            username = user
                            send_msg(conn, {'type': 'response', 'content': '登录成功'})
                            broadcast_online(user)
                else:
                    send_msg(conn, {'type': 'response', 'content': '用户名或密码错误'})
            elif msg_type == 'private':
                if username:
                    msg['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    forward_private(msg)
            elif msg_type == 'group':
                if username:
                    msg['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    broadcast_group(msg)
            elif msg_type == 'list':
                if username:
                    send_online_list(conn)
            elif msg_type == 'logout':
                break
    except Exception as e:
        print(f'客户端 {addr} 异常: {e}')
    finally:
        if username:
            with lock:
                online_users.pop(username, None)
            broadcast_offline(username)
        conn.close()
        print(f'客户端 {addr} 断开连接')

if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(100)
    print(f'服务端启动，监听 {HOST}:{PORT}（仅本机可访问）')
    print(f'用户数据保存至: {USER_DB_FILE}')
    try:
        while True:
            conn, addr = server.accept()
            print(f'新连接来自 {addr}')
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print('服务端关闭')
    finally:
        server.close()