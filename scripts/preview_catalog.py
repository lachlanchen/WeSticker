"""Serve a built static PWA under its deployment prefix for offline QA."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    parser.add_argument("--port", type=int, default=18645)
    parser.add_argument("--base", default="/westicker/")
    args = parser.parse_args()
    if not args.base.startswith("/") or not args.base.endswith("/") or ".." in args.base:
        raise ValueError("Invalid path prefix")

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            return super().translate_path("/" + path[len(args.base):])

        def do_GET(self):
            if not urlsplit(self.path).path.startswith(args.base):
                self.send_error(404)
                return
            super().do_GET()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(args.directory.resolve())))
    print(f"http://127.0.0.1:{args.port}{args.base}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
