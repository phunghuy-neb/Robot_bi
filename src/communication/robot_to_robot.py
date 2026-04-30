"""Robot-to-robot LAN communication placeholder."""

from __future__ import annotations

import json
import logging
import socket
import time

logger = logging.getLogger(__name__)


class RobotToRobot:
    """Discovery and simple UDP messaging for other Robot Bi devices."""

    DISCOVERY_PORT = 45454

    def __init__(self):
        """Khoi tao communication manager."""
        self.connected: dict[str, dict] = {}

    def discover_robots(self, timeout_sec: int = 5) -> list[dict]:
        """Tim robot Bi khac trong LAN bang UDP broadcast."""
        robots = []
        sock = None
        try:
            timeout = max(0.05, min(float(timeout_sec), 0.2))
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            message = json.dumps({"type": "robot_bi_discover", "ts": time.time()}).encode("utf-8")
            sock.sendto(message, ("255.255.255.255", self.DISCOVERY_PORT))
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    data, addr = sock.recvfrom(2048)
                    payload = json.loads(data.decode("utf-8"))
                    if payload.get("type") == "robot_bi_hello":
                        robots.append({"ip": addr[0], "name": payload.get("name", "Robot Bi")})
                except socket.timeout:
                    break
                except Exception as exc:
                    logger.debug("[RobotToRobot] discovery packet ignored: %s", exc)
            return robots
        except PermissionError as exc:
            logger.debug("[RobotToRobot] discovery unavailable in sandbox: %s", exc)
            return []
        except Exception:
            logger.exception("[RobotToRobot] discover_robots failed")
            return []
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    logger.debug("[RobotToRobot] socket close ignored")

    def connect(self, robot_ip: str) -> bool:
        """Luu robot_ip vao danh sach connected."""
        try:
            if not robot_ip:
                return False
            self.connected[robot_ip] = {"ip": robot_ip, "connected_at": time.time()}
            return True
        except Exception:
            logger.exception("[RobotToRobot] connect failed")
            return False

    def send_message(self, robot_ip: str, message: str) -> bool:
        """Gui message UDP toi robot_ip."""
        sock = None
        try:
            if not robot_ip:
                return False
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = json.dumps({"type": "robot_bi_message", "message": str(message)}).encode("utf-8")
            sock.sendto(payload, (robot_ip, self.DISCOVERY_PORT))
            return True
        except PermissionError as exc:
            logger.debug("[RobotToRobot] send unavailable in sandbox: %s", exc)
            return False
        except Exception:
            logger.exception("[RobotToRobot] send_message failed")
            return False
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    logger.debug("[RobotToRobot] socket close ignored")

    def sync_behavior(self, robot_ip: str, behavior: str) -> bool:
        """Dong bo hanh vi giua 2 robot."""
        try:
            return self.send_message(robot_ip, json.dumps({"behavior": behavior}))
        except Exception:
            logger.exception("[RobotToRobot] sync_behavior failed")
            return False

    def get_connected_robots(self) -> list[dict]:
        """Tra ve danh sach robot da connect."""
        try:
            return list(self.connected.values())
        except Exception:
            logger.exception("[RobotToRobot] get_connected_robots failed")
            return []
