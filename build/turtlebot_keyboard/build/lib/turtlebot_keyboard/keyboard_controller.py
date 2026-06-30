#!/usr/bin/env python3

import select
import sys
import termios
import threading
import tty

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node


HELP = """
TurtleBot keyboard controller
-----------------------------
       W: forward
  A: left   D: right
       S: backward

Space or X: stop
Ctrl-C: quit

Linear speed:  0.01 m/s
Angular speed: 0.01 rad/s
"""


def velocity_for_key(key, speed):
    """Return linear and angular velocities for a supported key."""
    commands = {
        'w': (speed, 0.0),
        's': (-speed, 0.0),
        'a': (0.0, speed),
        'd': (0.0, -speed),
        ' ': (0.0, 0.0),
        'x': (0.0, 0.0),
    }
    return commands.get(key.lower())


class KeyboardController(Node):
    """Publish fixed TurtleBot velocity commands selected from the keyboard."""

    def __init__(self):
        super().__init__('keyboard_controller')
        self.declare_parameter('speed', 0.1)
        self.declare_parameter('publish_rate', 10.0)

        self.speed = float(self.get_parameter('speed').value)
        publish_rate = float(self.get_parameter('publish_rate').value)
        if self.speed < 0.0:
            raise ValueError('speed must be greater than or equal to zero')
        if publish_rate <= 0.0:
            raise ValueError('publish_rate must be greater than zero')

        self.publisher = self.create_publisher(TwistStamped, 'cmd_vel', 10)
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self._velocity_lock = threading.Lock()
        self.timer = self.create_timer(1.0 / publish_rate, self.publish_velocity)

    def set_command(self, linear_velocity, angular_velocity):
        """Set the command which is continuously published by the timer."""
        with self._velocity_lock:
            self.linear_velocity = linear_velocity
            self.angular_velocity = angular_velocity

    def publish_velocity(self):
        """Publish the current velocity command."""
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        with self._velocity_lock:
            message.twist.linear.x = self.linear_velocity
            message.twist.angular.z = self.angular_velocity
        self.publisher.publish(message)

    def stop(self):
        """Publish a final zero-velocity command immediately."""
        self.set_command(0.0, 0.0)
        self.publish_velocity()


def read_key(settings):
    """Wait for one key press while preserving the terminal configuration."""
    tty.setraw(sys.stdin.fileno())
    try:
        select.select([sys.stdin], [], [], None)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardController()

    if not sys.stdin.isatty():
        node.destroy_node()
        rclpy.shutdown()
        raise RuntimeError('keyboard_controller must be run in an interactive terminal')

    settings = termios.tcgetattr(sys.stdin)
    executor_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True,
    )
    executor_thread.start()

    print(HELP)
    try:
        while rclpy.ok():
            key = read_key(settings)
            if key == '\x03':
                break

            command = velocity_for_key(key, node.speed)
            if command is not None:
                node.set_command(*command)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.stop()
        node.destroy_node()
        rclpy.shutdown()
        executor_thread.join(timeout=1.0)


if __name__ == '__main__':
    main()
