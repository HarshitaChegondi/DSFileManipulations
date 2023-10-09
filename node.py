#!/usr/bin/env python3

import os
import sys
import rpyc
from time import time, sleep
from threading import Thread
from watchdog.events import FileSystemEventHandler

class ServerNode(rpyc.Service):
    def __init__(self, host="localhost", port=18862, dirname="server_files"):
        self.host = host
        self.port = port
        self.address = (host, port)

        self.fs_root = os.path.join(os.getcwd(), dirname)
        os.makedirs(self.fs_root, exist_ok=True)

        self.__intro__()

    def __intro__(self):
        print("\t", "="*3 + ">\t", "File Sync Service", "\t<" + "="*3, "\t", end="\n\n")
        print("Listening at \t:\t", f"[{self.host}:{self.port}]")
        print("Synchronized Folder \t:\t", f"<{os.path.basename(self.fs_root)}/>")
        print("+", "=" * 50, "+", end="\n\n")

    def on_connect(self, conn):
        print(f"[NEW] Client connected: <{conn}>")

    def on_disconnect(self, conn):
        print(f"[CLOSE] Client disconnected: <{conn}>")

    def exposed_upload(self, filename, content):
        print(f"[UPLOAD] File: <{filename}>")
        try:
            with open(file=os.path.join(self.fs_root, filename), mode="wb") as f:
                f.write(content)
            return b":uploaded"
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return b":failed"

    def exposed_download(self, filename):
        print(f"[DOWNLOAD] File: <{filename}>")
        try:
            with open(file=os.path.join(self.fs_root, filename), mode="rb") as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return b":failed"

    def exposed_delete(self, filename):
        print(f"[DELETE] File: <{filename}>")
        filepath = os.path.join(self.fs_root, filename)
        try:
            os.remove(filepath)
            return b":deleted"
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return b":failed"

    def exposed_rename(self, old_filename, new_filename):
        print(f"[RENAME] File: <from:{old_filename}> => <to:{new_filename}>")
        old_filepath = os.path.join(self.fs_root, old_filename)
        new_filepath = os.path.join(self.fs_root, new_filename)
        try:
            os.rename(old_filepath, new_filepath)
            return b":renamed"
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return b":failed"

class ClientNode:
    def __init__(self, host="localhost", port=18862, dirname="client_files"):
        self.host = host
        self.port = port
        self.address = (host, port)

        self.fs_root = os.path.join(os.getcwd(), dirname)
        os.makedirs(self.fs_root, exist_ok=True)

        self.conn = rpyc.connect(*self.address)

    def upload(self, filename):
        print("=>", f"Uploading file: {filename}")
        try:
            with open(file=os.path.join(self.fs_root, filename), mode="rb") as f:
                res = self.conn.root.upload(filename, f.read())
                self.conn.close()
                print(res, end="\n\n")
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    def download(self, filename): # Used only for integrety checks, not needed for now
        print("=>", f"Downloading file: {filename}")
        try:
            with open(file=os.path.join(self.fs_root, filename), mode="wb") as f:
                content = self.conn.root.download(filename)
                self.conn.close()
                if content != b":failed":
                    f.write(content)
                    print(b":downloaded", end="\n\n")
                else:
                    print(b":failed", end="\n\n")
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    def delete(self, filename):
        print("=>", f"Deleting file: {filename}")
        try:
            res = self.conn.root.delete(filename)
            self.conn.close()
            print(res, end="\n\n")
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    def rename(self, old_filename, new_filename):
        print("=>", f"Renaming file: <from:{old_filename}> <to:{new_filename}>")
        try:
            res = self.conn.root.rename(old_filename, new_filename)
            self.conn.close()
            print(res, end="\n\n")
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

class FSEventHandler(FileSystemEventHandler):
    def __init__(self, host, port):
        super().__init__()

        self.c_m_timer = time()
        self.host = host
        self.port = port

        self.__intro__()

    def __intro__(self):
        print("[ENABLE] Watchdog service", end="\n\n")

    def on_created(self, event):
        if event.is_directory:
            return None

        filename = os.path.basename(event.src_path)
        if filename[0] != '.': # ignore changes made to meta-file
            # Upload the newly created file to server
            print(f"New file created: [{filename}]")
            self.client = ClientNode(host=self.host, port=self.port)
            Thread(target=self.client.upload, args=[filename]).start() # helper thread
            self.c_m_timer = time()

    def on_modified(self, event):
        if event.is_directory:
            return None

        timer_gap = time() - self.c_m_timer
        if timer_gap < 1:
            return None

        filename = os.path.basename(event.src_path)
        if filename[0] != ".": # ignore changes made to meta-file
            # Upload the modified file to server
            # (no need for incremental updates)
            print(f"File content modified: [{filename}]")
            self.client = ClientNode(host=self.host, port=self.port)
            Thread(target=self.client.upload, args=[filename]).start() # helper thread
            self.c_m_timer = time()

    def on_deleted(self, event):
        if event.is_directory:
            return None

        filename = os.path.basename(event.src_path)
        if filename[0] != ".": # ignore changes made to meta-file
            # Delete the remote file at server
            print(f"File deleted: [{filename}]")
            self.client = ClientNode(host=self.host, port=self.port)
            Thread(target=self.client.delete, args=[filename]).start() # helper thread

    def on_moved(self, event):
        if event.is_directory:
            return None

        old, new = map(os.path.basename, [event.src_path, event.dest_path])
        if old[0] != ".": # ignore changes made to meta-file
            # Rename the remote file at server
            print(f"File renamed: [{old}] -> [{new}]")
            self.client = ClientNode(host=self.host, port=self.port)
            Thread(target=self.client.rename, args=[old, new]).start() # helper thread


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="FileShareService",
                                    description="Share files between a client and a server",
                                    epilog="[Ctrl-C] to close the app")

    parser.add_argument('-t', '--type', type=str, action='store', required=True, help='type of node [server/client]')
    parser.add_argument('-ip', '--host', type=str, action='store', default="localhost", help='host ip of server node')
    parser.add_argument('-p', '--port', type=int, action='store', default=18862, help='port number of server node')

    args = parser.parse_args()

    node_type = args.type.lower()
    host, port = args.host, args.port
    match node_type:
        case "server":
            from rpyc.utils.server import ThreadedServer

            server = ThreadedServer(ServerNode(host=host, port=port), port=port)
            server.start()
        case "client":
            from watchdog.observers import Observer

            TIMEOUT = 1 # second(s)

            watch_folder = os.path.join(os.getcwd(), "client_files")
            os.makedirs(watch_folder, exist_ok=True)

            observer = Observer()
            observer.schedule(FSEventHandler(host=host, port=port), watch_folder, recursive=False)
            observer.start() # Start watching for changes in the <watch_folder>

            # Watchdog loop
            try:
                while True:
                    sleep(TIMEOUT)
            except KeyboardInterrupt: # [Ctrl-C]
                observer.stop() # Stop the watcher

            observer.join() # Join the observer thread to main coroutine
        case _:
            print(f"[ERROR] Node type not found: <{node_type}>", file=sys.stderr)
            sys.exit(1)
