#include "nav_agent/vio_wrapper.hpp"

#include <geometry_msgs/msg/transform_stamped.hpp>

// ── Optional VIO backend headers ─────────────────────────────────────────────
#ifdef USE_OPENVINS
#  include <ov_core/track/TrackDescriptor.h>
#  include <ov_msckf/core/VioManager.h>
#  include <ov_msckf/core/VioManagerOptions.h>
#endif

#ifdef USE_ORBSLAM3
#  include <ORB_SLAM3/System.h>
#endif

// ─────────────────────────────────────────────────────────────────────────────

VIOWrapper::VIOWrapper() : Node("nav_agent") {
    // Declare ROS 2 parameters
    this->declare_parameter<std::string>("left_camera_topic",  "/airsim/camera/front_left/image_raw");
    this->declare_parameter<std::string>("right_camera_topic", "/airsim/camera/front_right/image_raw");
    this->declare_parameter<std::string>("imu_topic",          "/airsim/imu");
    this->declare_parameter<std::string>("odom_topic",         "/vio/odom");

    const auto left_topic  = this->get_parameter("left_camera_topic").as_string();
    const auto right_topic = this->get_parameter("right_camera_topic").as_string();
    const auto imu_topic   = this->get_parameter("imu_topic").as_string();
    const auto odom_topic  = this->get_parameter("odom_topic").as_string();

    left_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
        left_topic, 10,
        std::bind(&VIOWrapper::leftImageCb, this, std::placeholders::_1));

    right_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
        right_topic, 10,
        std::bind(&VIOWrapper::rightImageCb, this, std::placeholders::_1));

    imu_sub_ = this->create_subscription<sensor_msgs::msg::Imu>(
        imu_topic, rclcpp::SensorDataQoS(),
        std::bind(&VIOWrapper::imuCb, this, std::placeholders::_1));

    odom_pub_       = this->create_publisher<nav_msgs::msg::Odometry>(odom_topic, 10);
    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

    vio_thread_ = std::thread(&VIOWrapper::runVIO, this);

#if defined(USE_OPENVINS)
    RCLCPP_INFO(get_logger(), "VIO node started — backend: OpenVINS");
#elif defined(USE_ORBSLAM3)
    RCLCPP_INFO(get_logger(), "VIO node started — backend: ORB-SLAM3");
#else
    RCLCPP_WARN(get_logger(),
        "VIO node started — NO backend compiled. "
        "Rebuild with USE_OPENVINS or USE_ORBSLAM3 for real odometry. "
        "Publishing identity pose stub.");
#endif
}

VIOWrapper::~VIOWrapper() {
    running_ = false;
    if (vio_thread_.joinable()) {
        vio_thread_.join();
    }
}

// ── ROS callbacks ─────────────────────────────────────────────────────────────

void VIOWrapper::leftImageCb(const sensor_msgs::msg::Image::SharedPtr msg) {
    cv_bridge::CvImageConstPtr cv_ptr;
    try {
        cv_ptr = cv_bridge::toCvShare(msg, "mono8");
    } catch (const cv_bridge::Exception &e) {
        RCLCPP_ERROR(get_logger(), "cv_bridge left: %s", e.what());
        return;
    }
    const double ts = msg->header.stamp.sec + msg->header.stamp.nanosec * 1e-9;
    std::lock_guard<std::mutex> lk(img_mtx_);
    left_buf_.emplace_back(ts, cv_ptr->image.clone());
    if (left_buf_.size() > kMaxImgBuf) left_buf_.pop_front();
}

void VIOWrapper::rightImageCb(const sensor_msgs::msg::Image::SharedPtr msg) {
    cv_bridge::CvImageConstPtr cv_ptr;
    try {
        cv_ptr = cv_bridge::toCvShare(msg, "mono8");
    } catch (const cv_bridge::Exception &e) {
        RCLCPP_ERROR(get_logger(), "cv_bridge right: %s", e.what());
        return;
    }
    const double ts = msg->header.stamp.sec + msg->header.stamp.nanosec * 1e-9;
    std::lock_guard<std::mutex> lk(img_mtx_);
    right_buf_.emplace_back(ts, cv_ptr->image.clone());
    if (right_buf_.size() > kMaxImgBuf) right_buf_.pop_front();
}

void VIOWrapper::imuCb(const sensor_msgs::msg::Imu::SharedPtr msg) {
    ImuMeasurement m;
    m.timestamp = msg->header.stamp.sec + msg->header.stamp.nanosec * 1e-9;
    m.accel = {msg->linear_acceleration.x,
               msg->linear_acceleration.y,
               msg->linear_acceleration.z};
    m.gyro  = {msg->angular_velocity.x,
               msg->angular_velocity.y,
               msg->angular_velocity.z};
    std::lock_guard<std::mutex> lk(imu_mtx_);
    imu_buf_.push_back(m);
    if (imu_buf_.size() > kMaxImuBuf) imu_buf_.pop_front();
}

// ── Stereo sync ───────────────────────────────────────────────────────────────

bool VIOWrapper::trySyncPair(ImagePair &out) {
    std::lock_guard<std::mutex> lk(img_mtx_);
    if (left_buf_.empty() || right_buf_.empty()) return false;

    // Walk left buffer to find the oldest left frame that has a matching right.
    for (auto it_l = left_buf_.begin(); it_l != left_buf_.end(); ++it_l) {
        for (auto it_r = right_buf_.begin(); it_r != right_buf_.end(); ++it_r) {
            if (std::abs(it_l->first - it_r->first) <= kSyncTolSec) {
                out.timestamp = it_l->first;
                out.left      = std::move(it_l->second);
                out.right     = std::move(it_r->second);
                left_buf_.erase(it_l);
                right_buf_.erase(it_r);
                return true;
            }
        }
    }
    return false;
}

// ── VIO thread ────────────────────────────────────────────────────────────────

void VIOWrapper::runVIO() {
    while (running_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(33)); // ~30 Hz

        ImagePair pair;
        if (!trySyncPair(pair)) continue;

        // Collect IMU measurements up to pair.timestamp.
        std::vector<ImuMeasurement> imu_window;
        {
            std::lock_guard<std::mutex> lk(imu_mtx_);
            while (!imu_buf_.empty() && imu_buf_.front().timestamp <= pair.timestamp) {
                imu_window.push_back(imu_buf_.front());
                imu_buf_.pop_front();
            }
        }

        // ── Backend integration ───────────────────────────────────────────────
        Eigen::Vector3d    new_pos;
        Eigen::Quaterniond new_ori;
        Eigen::Vector3d    new_vel;

#if defined(USE_OPENVINS)
        // Feed stereo + IMU to OpenVINS.
        // Replace vio_manager_ with your VioManager instance.
        //
        // for (const auto &m : imu_window)
        //     vio_manager_->feed_measurement_imu({m.timestamp, m.accel, m.gyro});
        // vio_manager_->feed_measurement_stereo(pair.timestamp, pair.left, pair.right, 0, 1);
        //
        // auto state = vio_manager_->get_state();
        // new_pos = state->_imu->pos();
        // new_ori = state->_imu->quat();
        // new_vel = state->_imu->vel();
        (void)imu_window;
        RCLCPP_WARN_ONCE(get_logger(), "OpenVINS backend integration stub — wire vio_manager_ calls.");
        new_pos = pos_;
        new_ori = ori_;
        new_vel = vel_;

#elif defined(USE_ORBSLAM3)
        // Feed stereo + IMU to ORB-SLAM3.
        //
        // std::vector<ORB_SLAM3::IMU::Point> orb_imu;
        // for (const auto &m : imu_window)
        //     orb_imu.emplace_back(m.accel.cast<float>(), m.gyro.cast<float>(), m.timestamp);
        //
        // Sophus::SE3f Tcw = orb_slam3_->TrackStereo(pair.left, pair.right,
        //                                             pair.timestamp, orb_imu);
        // Sophus::SE3f Twc = Tcw.inverse();
        // new_pos = Twc.translation().cast<double>();
        // Eigen::Quaternionf qf(Twc.rotationMatrix());
        // new_ori = qf.cast<double>();
        // new_vel = vel_;  // ORB-SLAM3 does not directly expose velocity
        (void)imu_window;
        RCLCPP_WARN_ONCE(get_logger(), "ORB-SLAM3 backend integration stub — wire orb_slam3_ calls.");
        new_pos = pos_;
        new_ori = ori_;
        new_vel = vel_;

#else
        // No VIO backend: publish identity pose with very high covariance
        // so the EKF treats this source as essentially uninformative.
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000 /* ms */,
            "VIO stub: no backend compiled. Odometry is identity. "
            "Install OpenVINS or ORB-SLAM3 and rebuild with USE_OPENVINS / USE_ORBSLAM3.");
        (void)imu_window;
        new_pos = pos_;
        new_ori = ori_;
        new_vel = vel_;
#endif

        // Commit updated state.
        {
            std::lock_guard<std::mutex> lk(state_mtx_);
            pos_ = new_pos;
            ori_ = new_ori;
            vel_ = new_vel;
        }

        const rclcpp::Time stamp(
            static_cast<int32_t>(pair.timestamp),
            static_cast<uint32_t>((pair.timestamp - static_cast<int32_t>(pair.timestamp)) * 1e9));
        publishOdom(stamp, new_pos, new_ori, new_vel);
    }
}

// ── Publish helpers ───────────────────────────────────────────────────────────

void VIOWrapper::publishOdom(const rclcpp::Time &stamp,
                              const Eigen::Vector3d &pos,
                              const Eigen::Quaterniond &ori,
                              const Eigen::Vector3d &vel)
{
    nav_msgs::msg::Odometry odom;
    odom.header.stamp    = stamp;
    odom.header.frame_id = "odom";
    odom.child_frame_id  = "base_link";

    odom.pose.pose.position.x    = pos.x();
    odom.pose.pose.position.y    = pos.y();
    odom.pose.pose.position.z    = pos.z();
    odom.pose.pose.orientation.x = ori.x();
    odom.pose.pose.orientation.y = ori.y();
    odom.pose.pose.orientation.z = ori.z();
    odom.pose.pose.orientation.w = ori.w();

    odom.twist.twist.linear.x = vel.x();
    odom.twist.twist.linear.y = vel.y();
    odom.twist.twist.linear.z = vel.z();

#if defined(USE_OPENVINS) || defined(USE_ORBSLAM3)
    // Covariances populated by the backend; use small defaults for the stub.
    const double pos_var = 0.01;
    const double rot_var = 0.001;
#else
    // Very high covariance signals to EKF that this source is unreliable.
    const double pos_var = 1e6;
    const double rot_var = 1e6;
#endif
    odom.pose.covariance[0]  = pos_var;
    odom.pose.covariance[7]  = pos_var;
    odom.pose.covariance[14] = pos_var;
    odom.pose.covariance[21] = rot_var;
    odom.pose.covariance[28] = rot_var;
    odom.pose.covariance[35] = rot_var;

    odom_pub_->publish(odom);

    // TF: odom → base_link
    geometry_msgs::msg::TransformStamped tf;
    tf.header              = odom.header;
    tf.child_frame_id      = "base_link";
    tf.transform.translation.x = pos.x();
    tf.transform.translation.y = pos.y();
    tf.transform.translation.z = pos.z();
    tf.transform.rotation      = odom.pose.pose.orientation;
    tf_broadcaster_->sendTransform(tf);
}
