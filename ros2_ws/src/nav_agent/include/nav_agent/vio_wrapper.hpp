#pragma once
#include <atomic>
#include <deque>
#include <mutex>
#include <thread>
#include <utility>

#include <Eigen/Dense>
#include <cv_bridge/cv_bridge.h>
#include <image_transport/image_transport.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <opencv2/opencv.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_ros/transform_broadcaster.h>

// ── Sensor measurement structs ────────────────────────────────────────────────

struct ImuMeasurement {
    double timestamp;       // seconds since epoch
    Eigen::Vector3d accel;  // m/s²
    Eigen::Vector3d gyro;   // rad/s
};

struct ImagePair {
    double timestamp;
    cv::Mat left;
    cv::Mat right;
};

// ── VIOWrapper node ───────────────────────────────────────────────────────────
//
// Subscribes to:
//   /airsim/camera/front_left/image_raw   (sensor_msgs/Image)
//   /airsim/camera/front_right/image_raw  (sensor_msgs/Image)
//   /airsim/imu                           (sensor_msgs/Imu)
//
// Publishes:
//   /vio/odom   (nav_msgs/Odometry, ~30 Hz)
//
// Backend selection (cmake compile-time):
//   -DUSE_OPENVINS  →  feed measurements to OpenVINS VioManager
//   -DUSE_ORBSLAM3  →  feed measurements to ORB-SLAM3 stereo-inertial
//   (neither)       →  identity pose stub + WARN_ONCE on every cycle

class VIOWrapper : public rclcpp::Node {
public:
    VIOWrapper();
    ~VIOWrapper();

private:
    // ── ROS callbacks ─────────────────────────────────────────────────────────
    void leftImageCb(const sensor_msgs::msg::Image::SharedPtr msg);
    void rightImageCb(const sensor_msgs::msg::Image::SharedPtr msg);
    void imuCb(const sensor_msgs::msg::Imu::SharedPtr msg);

    // ── VIO thread ────────────────────────────────────────────────────────────
    void runVIO();

    // Returns true and fills `out` when a synced stereo pair is available.
    bool trySyncPair(ImagePair &out);

    // Build and publish an Odometry message.
    void publishOdom(const rclcpp::Time &stamp,
                     const Eigen::Vector3d &pos,
                     const Eigen::Quaterniond &ori,
                     const Eigen::Vector3d &vel);

    // ── Subscriptions / publishers ────────────────────────────────────────────
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr left_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr right_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr    imu_sub_;
    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr     odom_pub_;
    std::unique_ptr<tf2_ros::TransformBroadcaster>            tf_broadcaster_;

    // ── Thread-safe sensor buffers ────────────────────────────────────────────
    std::mutex                                    imu_mtx_;
    std::deque<ImuMeasurement>                    imu_buf_;

    std::mutex                                    img_mtx_;
    std::deque<std::pair<double, cv::Mat>>        left_buf_;
    std::deque<std::pair<double, cv::Mat>>        right_buf_;

    // Maximum frames kept in each image buffer before oldest is dropped.
    static constexpr std::size_t kMaxImgBuf        = 30;
    // Maximum IMU measurements kept (200 Hz × 1 s buffer = 200).
    static constexpr std::size_t kMaxImuBuf        = 400;
    // Left/right images are considered synced if |Δt| ≤ this value (seconds).
    static constexpr double      kSyncTolSec       = 0.005;

    // ── Estimated state (updated by VIO thread) ───────────────────────────────
    std::mutex         state_mtx_;
    Eigen::Vector3d    pos_{0.0, 0.0, 0.0};
    Eigen::Quaterniond ori_{Eigen::Quaterniond::Identity()};
    Eigen::Vector3d    vel_{0.0, 0.0, 0.0};

    // ── Lifecycle ─────────────────────────────────────────────────────────────
    std::thread        vio_thread_;
    std::atomic<bool>  running_{true};
};
