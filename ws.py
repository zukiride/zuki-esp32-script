import usocket as socket
import ubinascii
import urandom

class WebSocket:
    def __init__(self, url):
        self.url = url
        self.socket = None
        self._connect()

    def _connect(self):
        proto, dummy, host, path = self.url.split("/", 3)
        if proto == "ws:":
            port = 80
        else:
            raise ValueError("Unsupported protocol: " + proto)

        if ":" in host:
            host, port = host.split(":", 1)
            port = int(port)

        ai = socket.getaddrinfo(host, port)
        addr = ai[0][-1]

        self.socket = socket.socket()
        self.socket.connect(addr)

        key = ubinascii.b2a_base64(urandom.bytes(16))
        key = key.decode().strip()

        headers = [
            "GET /{} HTTP/1.1".format(path),
            "Host: {}:{}".format(host, port),
            "Connection: Upgrade",
            "Upgrade: websocket",
            "Sec-WebSocket-Key: {}".format(key),
            "Sec-WebSocket-Version: 13",
            "",
            ""
        ]

        self.socket.write('\r\n'.join(headers).encode())

        response = self.socket.read(4096).decode()
        if "101 Switching Protocols" not in response:
            raise Exception("WebSocket handshake failed")

    def send(self, data):
        self.socket.write(b"\x81")
        length = len(data)
        if length < 126:
            self.socket.write(bytes([length]))
        elif length < 65536:
            self.socket.write(b"\x7e")
            self.socket.write(length.to_bytes(2, "big"))
        else:
            self.socket.write(b"\x7f")
            self.socket.write(length.to_bytes(8, "big"))
        self.socket.write(data.encode())

    def receive(self):
        opcode = self.socket.read(1)[0] & 0x0F
        length = self.socket.read(1)[0] & 0x7F
        if length == 126:
            length = int.from_bytes(self.socket.read(2), "big")
        elif length == 127:
            length = int.from_bytes(self.socket.read(8), "big")
        mask = self.socket.read(4)
        data = self.socket.read(length)
        return bytes(b ^ mask[i % 4] for i, b in enumerate(data)).decode()

    def close(self):
        self.socket.close()