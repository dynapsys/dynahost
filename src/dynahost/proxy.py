import socket
import threading
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger("dynahost.proxy")


class TcpForwarder:
    """Simple multi-threaded TCP forwarder.

    Listens on (listen_host, listen_port) and forwards to (target_host, target_port).
    """

    def __init__(self, listen: Tuple[str, int], target: Tuple[str, int], buffer_size: int = 65536):
        self.listen_host, self.listen_port = listen
        self.target_host, self.target_port = target
        self.buffer_size = buffer_size
        self._server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _pipe(self, src: socket.socket, dst: socket.socket):
        try:
            while not self._stop.is_set():
                data = src.recv(self.buffer_size)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except Exception:
                pass

    def _handle_client(self, client_sock: socket.socket):
        try:
            upstream = socket.create_connection((self.target_host, self.target_port))
        except Exception as e:
            logger.warning("Forward connect failed to %s:%d: %s", self.target_host, self.target_port, e)
            client_sock.close()
            return

        t1 = threading.Thread(target=self._pipe, args=(client_sock, upstream), daemon=True)
        t2 = threading.Thread(target=self._pipe, args=(upstream, client_sock), daemon=True)
        t1.start(); t2.start()
        t1.join(); t2.join()
        try:
            upstream.close()
        except Exception:
            pass
        try:
            client_sock.close()
        except Exception:
            pass

    def _serve(self):
        logger.info("Starting TCP forwarder %s:%d -> %s:%d", self.listen_host, self.listen_port, self.target_host, self.target_port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self._server_sock = s
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.listen_host, self.listen_port))
            s.listen(128)
            s.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    client, _addr = s.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
        logger.info("Forwarder stopped %s:%d", self.listen_host, self.listen_port)

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2)


class TcpForwarderManager:
    def __init__(self):
        self.forwarders: List[TcpForwarder] = []

    def add(self, listen_host: str, listen_port: int, target_host: str, target_port: int) -> TcpForwarder:
        fwd = TcpForwarder((listen_host, listen_port), (target_host, target_port))
        fwd.start()
        self.forwarders.append(fwd)
        return fwd

    def stop_all(self):
        for f in self.forwarders:
            try:
                f.stop()
            except Exception:
                pass
