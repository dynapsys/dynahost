import socket
import ssl
import threading
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("dynahost.terminator")


class TlsTerminator:
    """Accept TLS on (listen_host, listen_port) and forward plaintext to target.

    This allows exposing HTTPS externally while forwarding to a plaintext HTTP
    service internally.
    """

    def __init__(
        self,
        listen: Tuple[str, int],
        target: Tuple[str, int],
        ssl_context: ssl.SSLContext,
        buffer_size: int = 65536,
    ):
        self.listen_host, self.listen_port = listen
        self.target_host, self.target_port = target
        self.ctx = ssl_context
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

    def _serve(self):
        logger.info(
            "Starting TLS terminator %s:%d -> %s:%d",
            self.listen_host,
            self.listen_port,
            self.target_host,
            self.target_port,
        )
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
                # Wrap client in TLS
                try:
                    tls_client = self.ctx.wrap_socket(client, server_side=True)
                except ssl.SSLError as e:
                    logger.warning("TLS handshake failed: %s", e)
                    try:
                        client.close()
                    except Exception:
                        pass
                    continue

                # Connect upstream (plaintext)
                try:
                    upstream = socket.create_connection((self.target_host, self.target_port))
                except Exception as e:
                    logger.warning("Connect failed to %s:%d: %s", self.target_host, self.target_port, e)
                    try:
                        tls_client.close()
                    except Exception:
                        pass
                    continue

                t1 = threading.Thread(target=self._pipe, args=(tls_client, upstream), daemon=True)
                t2 = threading.Thread(target=self._pipe, args=(upstream, tls_client), daemon=True)
                t1.start(); t2.start()
                t1.join(); t2.join()
                try:
                    upstream.close()
                except Exception:
                    pass
                try:
                    tls_client.close()
                except Exception:
                    pass
        logger.info("TLS terminator stopped %s:%d", self.listen_host, self.listen_port)

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


class TlsTerminatorManager:
    def __init__(self):
        self.terms: list[TlsTerminator] = []

    def add(self, listen_host: str, listen_port: int, target_host: str, target_port: int, ssl_context: ssl.SSLContext) -> TlsTerminator:
        t = TlsTerminator((listen_host, listen_port), (target_host, target_port), ssl_context)
        t.start()
        self.terms.append(t)
        return t

    def stop_all(self):
        for t in self.terms:
            try:
                t.stop()
            except Exception:
                pass
