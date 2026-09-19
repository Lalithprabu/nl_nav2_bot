"""Simple CLI front-end: type a command, it's published to /nl_command.

This stands in for a voice/chat front-end so the system is usable and
testable without any speech recognition setup. Swap this node out for a
speech-to-text node later without touching nl_command_node.py at all.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TextInputNode(Node):

    def __init__(self):
        super().__init__('text_input_node')
        self._pub = self.create_publisher(String, 'nl_command', 10)
        self.create_subscription(String, 'nl_command_status', self._on_status, 10)
        self.get_logger().info(
            'Type a command (e.g. "go to the kitchen") and press Enter. '
            'Ctrl+C to quit.'
        )

    def _on_status(self, msg: String):
        print(f'[status] {msg.data}')

    def run(self):
        try:
            while rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.1)
                try:
                    text = input('> ')
                except EOFError:
                    break
                if not text.strip():
                    continue
                msg = String()
                msg.data = text
                self._pub.publish(msg)
        except KeyboardInterrupt:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = TextInputNode()
    node.run()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
