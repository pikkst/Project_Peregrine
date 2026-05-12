import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseWithCovarianceStamped
from cv_bridge import CvBridge
import sys

from savepoint_agent.inference.vpr_inference import VPRModel

class SavepointNode(Node):
    def __init__(self):
        super().__init__('savepoint_agent')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image,
            '/airsim/camera/front_left/image_raw',
            self.image_callback,
            10
        )
        self.pub = self.create_publisher(
            PoseWithCovarianceStamped,
            '/localization/landmark_fix',
            10
        )
        self.model = VPRModel(db_path='sim/savepoint_database', logger=self.get_logger())
        self.model.load_database()
        self.get_logger().info('Savepoint Agent initialized')

    def image_callback(self, msg: Image):
        try:
            pose, cov = self.model.infer(msg)
        except Exception as e:
            self.get_logger().error(f'VPR inference failed: {e}')
            return

        out = PoseWithCovarianceStamped()
        out.header = msg.header
        out.pose.pose.position.x = float(pose[0])
        out.pose.pose.position.y = float(pose[1])
        out.pose.pose.position.z = float(pose[2])
        out.pose.pose.orientation.x = float(pose[3])
        out.pose.pose.orientation.y = float(pose[4])
        out.pose.pose.orientation.z = float(pose[5])
        out.pose.pose.orientation.w = float(pose[6])
        flat = cov.flatten().tolist()
        out.pose.covariance = flat + [0.0] * (36 - len(flat))
        self.pub.publish(out)

def main(args=None):
    rclpy.init(args=args)
    node = SavepointNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
