import socket
import threading
import json
import sys

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345

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

def receiver(sock, stop_event):
    while not stop_event.is_set():
        try:
            msg = recv_msg(sock)
            if not msg:
                break
            t = msg.get('type')
            if t == 'private':
                print(f"\n[私聊] {msg['sender']} {msg['timestamp']}:\n  {msg['content']}")
            elif t == 'group':
                print(f"\n[群聊] {msg['sender']} {msg['timestamp']}:\n  {msg['content']}")
            elif t == 'response':
                print(f"\n[系统] {msg['content']}")
        except:
            break
    print('\n与服务器的连接已断开，按回车退出...')

def login_menu(sock):
    while True:
        print('\n===== 简易即时通信 =====')
        print('1. 登录')
        print('2. 注册')
        print('3. 退出')
        choice = input('请选择: ').strip()
        if choice == '1':
            user = input('用户名: ').strip()
            pwd = input('密码: ').strip()
            send_msg(sock, {'type': 'login', 'sender': user, 'password': pwd})
            resp = recv_msg(sock)
            if resp and resp.get('content') == '登录成功':
                print('登录成功！')
                return user
            else:
                print('登录失败:', resp.get('content') if resp else '无响应')
        elif choice == '2':
            user = input('新用户名: ').strip()
            pwd = input('新密码: ').strip()
            send_msg(sock, {'type': 'register', 'sender': user, 'password': pwd})
            resp = recv_msg(sock)
            print('系统:', resp.get('content') if resp else '无响应')
        elif choice == '3':
            sock.close()
            sys.exit(0)
        else:
            print('无效选项')

def chat_loop(sock, username, stop_event):
    print('\n进入聊天界面（输入 /quit 退出，/help 查看帮助）')
    while not stop_event.is_set():
        try:
            line = input()
        except EOFError:
            break
        if not line:
            continue
        line = line.strip()
        if line.startswith('/'):
            parts = line.split(maxsplit=2)
            cmd = parts[0].lower()
            if cmd == '/quit':
                send_msg(sock, {'type': 'logout', 'sender': username})
                break
            elif cmd == '/list':
                send_msg(sock, {'type': 'list', 'sender': username})
            elif cmd == '/group':
                if len(parts) > 1:
                    content = parts[1]
                    send_msg(sock, {'type': 'group', 'sender': username, 'receiver': 'all', 'content': content})
                else:
                    print('用法: /group <消息>')
            elif cmd == '/send':
                if len(parts) >= 3:
                    target = parts[1]
                    content = parts[2]
                    send_msg(sock, {'type': 'private', 'sender': username, 'receiver': target, 'content': content})
                else:
                    print('用法: /send <用户名> <消息>')
            elif cmd == '/help':
                print('命令列表:')
                print('  /send <用户名> <消息>  -> 私聊')
                print('  /group <消息>           -> 群聊')
                print('  /list                   -> 查看在线用户')
                print('  /quit                   -> 退出')
            else:
                print('未知命令，输入 /help 查看帮助')
        else:
            print('普通消息请以命令开头，如 /send 或 /group')

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_HOST, SERVER_PORT))
    except ConnectionRefusedError:
        print('无法连接服务器，请确认服务端已启动')
        sys.exit(1)

    username = login_menu(sock)
    stop_event = threading.Event()
    recv_thread = threading.Thread(target=receiver, args=(sock, stop_event), daemon=True)
    recv_thread.start()
    chat_loop(sock, username, stop_event)
    stop_event.set()
    sock.close()
    print('客户端已退出')