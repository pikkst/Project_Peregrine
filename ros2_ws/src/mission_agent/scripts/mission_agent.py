import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

MAX_SPEED = 2.0   # m/s
ARRIVAL_THRESHOLD = 0.1  # m — distance at which a waypoint is considered reached


def compute_velocity(
    dx: float, dy: float,
    gain: float = 0.3,
    max_speed: float = MAX_SPEED,
) -> tuple[float, float]:
    """Pure navigation math: proportional controller with speed clamping.

    Returns (vx, vy) in m/s.
    """
    vx = gain * dx
    vy = gain * dy
    speed = (vx ** 2 + vy ** 2) ** 0.5
    if speed > max_speed:
        scale = max_speed / speed
        vx *= scale
        vy *= scale
    return vx, vy


class MissionAgent(Node):
    def __init__(self):
        super().__init__('mission_agent')
        self.sub = self.create_subscription(
            Odometry,
            '/odometry/filtered',
            self.odom_callback,
            10
        )
        self.pub = self.create_publisher(
            Twist,
            '/airsim_node/drone_1/vel_cmd_body_frame',
            10
        )
        self.waypoints = [
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
        ]
        self.current_wp_idx = 0
        self.get_logger().info('Mission Agent initialized')

    def odom_callback(self, msg: Odometry):
        if self.current_wp_idx >= len(self.waypoints):
            return
        target_x, target_y = self.waypoints[self.current_wp_idx]
        dx = target_x - msg.pose.pose.position.x
        dy = target_y - msg.pose.pose.position.y
        dist = (dx**2 + dy**2) ** 0.5

        cmd = Twist()
        if dist < ARRIVAL_THRESHOLD:
            self.get_logger().info(f"Reached waypoint {self.current_wp_idx}")
            self.current_wp_idx += 1
        else:
            cmd.linear.x, cmd.linear.y = compute_velocity(dx, dy)

        self.pub.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = MissionAgent()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
