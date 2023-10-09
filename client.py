#!/usr/bin/env python3

import time
import rpyc

def sync_rpc():
    PORT = 18863

    # Connect to the computation server
    conn = rpyc.connect("localhost", PORT)

    # Synchronous RPC: add(i, j)
    result_sync_add = conn.root.add(3, 4)
    print("add(3, 4)")
    print("Synchronous add result:", result_sync_add, end="\n\n")

    # Synchronous RPC: sort(array A)
    array_to_sort = [4, 2, 7, 1, 9]
    print("sort(4, 2, 7, 1, 9)")
    result_sync_sort = conn.root.sort(array_to_sort)
    print("Synchronous sort result:", result_sync_sort, end="\n\n")

    conn.close() # Synchronous RPC
    time.sleep(5)

def async_rpc():
    PORT = 18863

    # Connect to the computation server
    conn = rpyc.connect("localhost", PORT)

    # Asynchronous RPC: async_add(i, j)
    async_result_add = rpyc.async_(conn.root.add)(5, 6)
    print("add(5, 6)")
    time.sleep(5)
    print("Async add acknowledgment received.")
    result_async_add = async_result_add.value
    print("Asynchronous add result:", result_async_add, end="\n\n")

    # Asynchronous RPC: async_sort(array A)
    async_result_sort = rpyc.async_(conn.root.sort)([8, 3, 6, 2, 1])
    print("sort([8, 3, 6, 2, 1])")
    time.sleep(5)
    print("Async sort acknowledgment received.")
    result_async_sort = async_result_sort.value
    print("Asynchronous sort result:", result_async_sort)

    conn.close() # Asynchronous RPC

if __name__ == "__main__":
    sync_rpc()
    print("\n")
    async_rpc()
