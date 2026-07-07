"""Lab 4 helper - a tiny client that sends an absolute-URL GET through the proxy.

Lets you exercise the proxy without configuring a browser. Sends
"GET http://host:port/path HTTP/1.1" to the proxy and prints the response, so
you can observe X-Cache: MISS on the first request and X-Cache: HIT on repeats.

Run:
    python proxy_client.py --proxy-port 8888 --url http://127.0.0.1:8080/HelloWorld.html
"""

import argparse
import socket
from urllib.parse import urlparse


def fetch_via_proxy(proxy_host: str, proxy_port: int, url: str) -> bytes:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 80
    request = (
        f"GET {url} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((proxy_host, proxy_port))
        s.sendall(request.encode("utf-8"))
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy test client")
    parser.add_argument("--proxy-host", default="127.0.0.1")
    parser.add_argument("--proxy-port", type=int, default=8888)
    parser.add_argument("--url", default="http://127.0.0.1:8080/HelloWorld.html")
    args = parser.parse_args()
    response = fetch_via_proxy(args.proxy_host, args.proxy_port, args.url)
    print(response.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
