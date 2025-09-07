import socket
import threading
import time

from dynahost.proxy import TcpForwarder, TcpForwarderManager


def _start_tcp_echo_server(host: str, port: int):
    def serve():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(5)
            conn, _ = s.accept()
            with conn:
                data = conn.recv(1024)
                conn.sendall(b"echo:" + data)
    t = threading.Thread(target=serve, daemon=True)
    t.start()
    time.sleep(0.05)
    return t


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_tcp_forwarder_loopback():
    backend_port = _get_free_port()
    forward_port = _get_free_port()

    # Start backend echo server
    _start_tcp_echo_server("127.0.0.1", backend_port)

    # Forward 127.0.0.1:forward_port -> 127.0.0.1:backend_port
    mgr = TcpForwarderManager()
    mgr.add("127.0.0.1", forward_port, "127.0.0.1", backend_port)

    time.sleep(0.05)

    # Connect to forwarder and send data
    with socket.create_connection(("127.0.0.1", forward_port), timeout=1) as c:
        c.sendall(b"hello")
        data = c.recv(1024)
    assert data == b"echo:hello"

    mgr.stop_all()
