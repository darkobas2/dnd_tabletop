"""IPC Bridge — localhost TCP socket for parent (Qt) <-> child (Ursina 3D) communication.

Protocol: newline-delimited JSON messages over TCP.
Messages:
  Parent -> Child: state_update, fog_update, token_move, token_add, token_remove,
                   creature_update, initiative_update, combat_update
  Child -> Parent: token_moved, token_selected, ready
"""

import json
import socket
import threading
import time
from typing import Callable, Dict, Optional, Any


DEFAULT_PORT = 0  # OS-assigned port


class IPCServer:
    """Runs in the Qt parent process. Accepts one connection from the 3D subprocess."""

    def __init__(self, on_message: Optional[Callable[[Dict], None]] = None):
        self.on_message = on_message
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(('127.0.0.1', DEFAULT_PORT))
        self._socket.listen(1)
        self.port = self._socket.getsockname()[1]
        self._client: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._buffer = ""

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        self._socket.settimeout(1.0)
        while self._running:
            try:
                self._client, addr = self._socket.accept()
                self._client.settimeout(0.5)
                self._read_loop()
            except socket.timeout:
                continue
            except OSError:
                break

    def _read_loop(self):
        while self._running and self._client:
            try:
                data = self._client.recv(4096)
                if not data:
                    break
                self._buffer += data.decode('utf-8')
                while '\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            if self.on_message:
                                self.on_message(msg)
                        except json.JSONDecodeError:
                            pass
            except socket.timeout:
                continue
            except (ConnectionResetError, OSError):
                break

    def send(self, message: Dict):
        if self._client:
            try:
                data = json.dumps(message) + '\n'
                self._client.sendall(data.encode('utf-8'))
            except (BrokenPipeError, OSError):
                pass

    def stop(self):
        self._running = False
        if self._client:
            try:
                self._client.close()
            except OSError:
                pass
        try:
            self._socket.close()
        except OSError:
            pass
        if self._thread:
            self._thread.join(timeout=2.0)

    @property
    def connected(self) -> bool:
        return self._client is not None


class IPCClient:
    """Runs in the 3D subprocess. Connects to the parent's TCP server."""

    def __init__(self, port: int, on_message: Optional[Callable[[Dict], None]] = None):
        self.port = port
        self.on_message = on_message
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._buffer = ""

    def connect(self, retries: int = 5, delay: float = 0.5) -> bool:
        for attempt in range(retries):
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.connect(('127.0.0.1', self.port))
                self._socket.settimeout(0.5)
                self._running = True
                self._thread = threading.Thread(target=self._read_loop, daemon=True)
                self._thread.start()
                self.send({"type": "ready"})
                return True
            except (ConnectionRefusedError, OSError):
                if attempt < retries - 1:
                    time.sleep(delay)
        return False

    def _read_loop(self):
        while self._running and self._socket:
            try:
                data = self._socket.recv(4096)
                if not data:
                    break
                self._buffer += data.decode('utf-8')
                while '\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            if self.on_message:
                                self.on_message(msg)
                        except json.JSONDecodeError:
                            pass
            except socket.timeout:
                continue
            except (ConnectionResetError, OSError):
                break

    def send(self, message: Dict):
        if self._socket:
            try:
                data = json.dumps(message) + '\n'
                self._socket.sendall(data.encode('utf-8'))
            except (BrokenPipeError, OSError):
                pass

    def stop(self):
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)


# Message factory helpers

def msg_state_update(encounter_dict: Dict) -> Dict:
    return {"type": "state_update", "encounter": encounter_dict}

def msg_fog_update(fog_grid: Any) -> Dict:
    return {"type": "fog_update", "fog": fog_grid}

def msg_token_move(creature_id: str, x: int, y: int) -> Dict:
    return {"type": "token_move", "creature_id": creature_id, "x": x, "y": y}

def msg_token_add(creature_dict: Dict) -> Dict:
    return {"type": "token_add", "creature": creature_dict}

def msg_token_remove(creature_id: str) -> Dict:
    return {"type": "token_remove", "creature_id": creature_id}

def msg_creature_update(creature_dict: Dict) -> Dict:
    return {"type": "creature_update", "creature": creature_dict}

def msg_initiative_update(order: list) -> Dict:
    return {"type": "initiative_update", "order": order}

def msg_token_moved(creature_id: str, x: int, y: int) -> Dict:
    return {"type": "token_moved", "creature_id": creature_id, "x": x, "y": y}
