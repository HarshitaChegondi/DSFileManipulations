#!/usr/bin/env python3

import rpyc

class ComputationService(rpyc.Service):
    def on_connect(self, conn):
        print(f"[NEW] client connection: {conn}")

    def on_disconnect(self, conn):
        print(f"[CLOSE] client connection: {conn}")

    def exposed_add(self, i, j):
        result = self.add(i, j)
        return result

    def exposed_sort(self, A):
        result = self.sort(A)
        return result

    def add(self, i, j):
        return i + j

    def sort(self, A):
        return sorted(A)

if __name__ == "__main__":
    from rpyc.utils.server import ThreadPoolServer

    PORT = 18863

    server = ThreadPoolServer(ComputationService, port=PORT)
    print(f"Starting computation server on port {PORT}...")
    server.start()
