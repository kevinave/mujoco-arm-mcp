"""The framing promise: recv_json returns one whole message however TCP chose
to split it. socketpair() gives two connected ends without a listener.
"""
import json
import socket
import threading
import time

from arm_common import recv_json, send_json


def test_recv_json_reassembles_a_message_arriving_in_pieces():
    a, b = socket.socketpair()
    try:
        # Larger than recv_json's 4096-byte reads, so reassembly is exercised
        # even if the kernel coalesces the writes.
        msg = {"cmd": "move", "angle1": 45.0, "angle2": -30.0, "pad": "x" * 9000}
        wire = (json.dumps(msg) + "\n").encode()
        pieces = [wire[i:i + 1024] for i in range(0, len(wire), 1024)]

        # Drip the pieces from another thread while recv_json blocks here, so
        # the reader really does see the message arrive fragment by fragment.
        def drip():
            for piece in pieces:
                a.sendall(piece)
                time.sleep(0.002)

        t = threading.Thread(target=drip)
        t.start()
        received = recv_json(b)
        t.join()

        assert received == msg
    finally:
        a.close()
        b.close()


def test_send_json_recv_json_round_trip():
    a, b = socket.socketpair()
    try:
        send_json(a, {"cmd": "get"})
        assert recv_json(b) == {"cmd": "get"}
    finally:
        a.close()
        b.close()
