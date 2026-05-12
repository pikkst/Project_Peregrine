import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, Imu
from cv_bridge import CvBridge
import numpy as np
import airsim
import time

class AirSimBridge(Node):
    def __init__(self):
        super().__init__('airsim_bridge')
        self.bridge = CvBridge()
        self.left_image_pub = self.create_publisher(Image, '/airsim/camera/front_left/image_raw', 10)
        self.right_image_pub = self.create_publisher(Image, '/airsim/camera/front_right/image_raw', 10)
        self.imu_pub = self.create_publisher(Imu, '/airsim/imu', 10)
        
        # Connect to AirSim
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True)
        self.client.armDisarm(True)
        
        # Timer to publish data at 30 Hz
        self.timer = self.create_timer(1.0/30.0, self.timer_callback)
        self.get_logger().info('AirSim Bridge Node has been started')

    def timer_callback(self):
        now = self.get_clock().now().to_msg()
        try:
            # Get images from AirSim
            responses = self.client.simGetImages([
                airsim.ImageRequest("0", airsim.ImageType.Scene, False, False),  # left camera
                airsim.ImageRequest("1", airsim.ImageType.Scene, False, False)   # right camera
            ])

            if len(responses) >= 2:
                # Process left image
                img1d = np.frombuffer(responses[0].image_data_uint8, dtype=np.uint8)
                img_rgb = img1d.reshape(responses[0].height, responses[0].width, 3)
                img_msg = self.bridge.cv2_to_imgmsg(img_rgb, encoding="rgb8")
                img_msg.header.stamp = now
                img_msg.header.frame_id = "front_left_camera"
                self.left_image_pub.publish(img_msg)

                # Process right image
                img1d = np.frombuffer(responses[1].image_data_uint8, dtype=np.uint8)
                img_rgb = img1d.reshape(responses[1].height, responses[1].width, 3)
                img_msg = self.bridge.cv2_to_imgmsg(img_rgb, encoding="rgb8")
                img_msg.header.stamp = now
                img_msg.header.frame_id = "front_right_camera"
                self.right_image_pub.publish(img_msg)

            # Get IMU data
            imu_data = self.client.getImuData()
            imu_msg = Imu()
            imu_msg.header.stamp = now
            imu_msg.header.frame_id = "imu_link"
            imu_msg.orientation.x = imu_data.orientation.x_val
            imu_msg.orientation.y = imu_data.orientation.y_val
            imu_msg.orientation.z = imu_data.orientation.z_val
            imu_msg.orientation.w = imu_data.orientation.w_val
            imu_msg.angular_velocity.x = imu_data.angular_velocity.x_val
            imu_msg.angular_velocity.y = imu_data.angular_velocity.y_val
            imu_msg.angular_velocity.z = imu_data.angular_velocity.z_val
            imu_msg.linear_acceleration.x = imu_data.linear_acceleration.x_val
            imu_msg.linear_acceleration.y = imu_data.linear_acceleration.y_val
            imu_msg.linear_acceleration.z = imu_data.linear_acceleration.z_val
            # Set covariance diagonal (values from vio_config.yaml imu noise params)
            imu_msg.orientation_covariance[0] = 0.01
            imu_msg.orientation_covariance[4] = 0.01
            imu_msg.orientation_covariance[8] = 0.01
            imu_msg.angular_velocity_covariance[0] = 1e-4
            imu_msg.angular_velocity_covariance[4] = 1e-4
            imu_msg.angular_velocity_covariance[8] = 1e-4
            imu_msg.linear_acceleration_covariance[0] = 1e-3
            imu_msg.linear_acceleration_covariance[4] = 1e-3
            imu_msg.linear_acceleration_covariance[8] = 1e-3
            self.imu_pub.publish(imu_msg)
        except Exception as e:
            self.get_logger().error(f'AirSim bridge error: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = AirSimBridge()
    try:
        rclpy.spin(node)
    finally:
        node.client.enableApiControl(False)
        rclpy.shutdown()

if __name__ == '__main__':
    main()