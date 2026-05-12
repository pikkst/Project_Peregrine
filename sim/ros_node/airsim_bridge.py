#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, Imu
from nav_msgs.msg import Odometry
import airsim
import numpy as np
import cv2
from cv_bridge import CvBridge

class AirSimBridge(Node):
    def __init__(self):
        super().__init__('airsim_bridge')
        self.bridge = CvBridge()
        # Initialize AirSim client
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True)
        self.client.armDisarm(True)
        
        # Publishers
        self.image_pub = self.create_publisher(Image, '/airsim/camera/image_raw', 10)
        self.imu_pub = self.create_publisher(Imu, '/airsim/imu', 10)
        self.odom_pub = self.create_publisher(Odometry, '/airsim/odom', 10)
        
        # Timer to publish at 30Hz
        self.timer = self.create_timer(1.0/30.0, self.publish_data)
        
    def publish_data(self):
        try:
            # Get images
            responses = self.client.simGetImages([
                airsim.ImageRequest(0, airsim.ImageType.Scene, False, False)
            ])
            if responses and len(responses) > 0:
                img = responses[0]
                img1d = np.frombuffer(img.image_data_uint8, dtype=np.uint8)
                img_rgb = img1d.reshape(img.height, img.width, 3)
                # Convert to ROS Image message
                img_msg = self.bridge.cv2_to_imgmsg(img_rgb, encoding='rgb8')
                img_msg.header.stamp = self.get_clock().now().to_msg()
                img_msg.header.frame_id = 'camera_frame'
                self.image_pub.publish(img_msg)
            
            # Get IMU data
            imu_data = self.client.getImuData()
            imu_msg = Imu()
            imu_msg.header.stamp = self.get_clock().now().to_msg()
            imu_msg.header.frame_id = 'imu_link'
            imu_msg.orientation.x = imu_data.orientation.x_val
            imu_msg.orientation.y = imu_data.orientation.y_val
            imu_msg.orientation.z = imu_data.orientation.z_val
            imu_msg.orientation.w = imu_data.orientation.w_val
            imu_msg.linear_acceleration.x = imu_data.linear_acceleration.x_val
            imu_msg.linear_acceleration.y = imu_data.linear_acceleration.y_val
            imu_msg.linear_acceleration.z = imu_data.linear_acceleration.z_val
            imu_msg.angular_velocity.x = imu_data.angular_velocity.x_val
            imu_msg.angular_velocity.y = imu_data.angular_velocity.y_val
            imu_msg.angular_velocity.z = imu_data.angular_velocity.z_val
            self.imu_pub.publish(imu_msg)
            
            # Get odometry
            odom_data = self.client.getMultirotorState()
            odom_msg = Odometry()
            odom_msg.header.stamp = self.get_clock().now().to_msg()
            odom_msg.header.frame_id = 'odom'
            odom_msg.child_frame_id = 'base_link'
            odom_msg.pose.pose.position.x = odom_data.kinematics_estimated.position.x_val
            odom_msg.pose.pose.position.y = odom_data.kinematics_estimated.position.y_val
            odom_msg.pose.pose.position.z = odom_data.kinematics_estimated.position.z_val
            odom_msg.pose.pose.orientation.x = odom_data.kinematics_estimated.orientation.x_val
            odom_msg.pose.pose.orientation.y = odom_data.kinematics_estimated.orientation.y_val
            odom_msg.pose.pose.orientation.z = odom_data.kinematics_estimated.orientation.z_val
            odom_msg.pose.pose.orientation.w = odom_data.kinematics_estimated.orientation.w_val
            odom_msg.twist.twist.linear.x = odom_data.kinematics_estimated.linear_velocity.x_val
            odom_msg.twist.twist.linear.y = odom_data.kinematics_estimated.linear_velocity.y_val
            odom_msg.twist.twist.linear.z = odom_data.kinematics_estimated.linear_velocity.z_val
            odom_msg.twist.twist.angular.x = odom_data.kinematics_estimated.angular_velocity.x_val
            odom_msg.twist.twist.angular.y = odom_data.kinematics_estimated.angular_velocity.y_val
            odom_msg.twist.twist.angular.z = odom_data.kinematics_estimated.angular_velocity.z_val
            self.odom_pub.publish(odom_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error in AirSim bridge: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = AirSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
