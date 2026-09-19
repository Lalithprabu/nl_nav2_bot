"""ROS 2 node: listens for natural-language commands and drives Nav2.

Subscribes to /nl_command (std_msgs/String). Each message is parsed into a
target waypoint (see command_parser.py) and sent to Nav2's NavigateToPose
action server. Publishes feedback/result status on /nl_command_status so a
UI or voice front-end can report back to the user.
"""
import math
import os

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String

from nl_nav2_bot.command_parser import parse_command


def yaw_to_quaternion(yaw: float):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class NLCommandNode(Node):

    def __init__(self):
        super().__init__('nl_command_node')

        self.declare_parameter(
            'waypoints_file',
            os.path.join(
                get_package_share_directory('nl_nav2_bot'),
                'config', 'waypoints.yaml',
            ),
        )
        waypoints_path = self.get_parameter('waypoints_file').value
        with open(waypoints_path, 'r') as f:
            self.waypoints = yaml.safe_load(f)['waypoints']

        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._status_pub = self.create_publisher(String, 'nl_command_status', 10)
        self.create_subscription(String, 'nl_command', self._on_command, 10)

        self.get_logger().info(
            f'nl_command_node ready. Known locations: {list(self.waypoints.keys())}'
        )

    def _publish_status(self, text: str):
        msg = String()
        msg.data = text
        self._status_pub.publish(msg)
        self.get_logger().info(text)

    def _on_command(self, msg: String):
        command_text = msg.data
        names = list(self.waypoints.keys())
        result = parse_command(command_text, names)

        if result.waypoint is None:
            self._publish_status(
                f'Could not understand "{command_text}". '
                f'Known locations: {names}'
            )
            return

        self._publish_status(
            f'Understood "{command_text}" -> "{result.waypoint}" '
            f'(method={result.method}, confidence={result.confidence:.2f})'
        )
        self._send_goal(result.waypoint)

    def _send_goal(self, waypoint_name: str):
        wp = self.waypoints[waypoint_name]
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(wp['x'])
        pose.pose.position.y = float(wp['y'])
        qx, qy, qz, qw = yaw_to_quaternion(float(wp.get('yaw', 0.0)))
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        if not self._action_client.wait_for_server(timeout_sec=5.0):
            self._publish_status('Nav2 action server not available.')
            return

        goal = NavigateToPose.Goal()
        goal.pose = pose

        self._publish_status(f'Sending goal: navigate to "{waypoint_name}".')
        send_goal_future = self._action_client.send_goal_async(
            goal, feedback_callback=self._on_feedback,
        )
        send_goal_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._publish_status('Goal rejected by Nav2.')
            return
        result_future = goal_handle.get_result_future()
        result_future.add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        distance = feedback_msg.feedback.distance_remaining
        self.get_logger().debug(f'Distance remaining: {distance:.2f} m')

    def _on_result(self, future):
        status = future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self._publish_status('Arrived at destination.')
        else:
            self._publish_status(f'Navigation ended with status {status}.')


def main(args=None):
    rclpy.init(args=args)
    node = NLCommandNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
