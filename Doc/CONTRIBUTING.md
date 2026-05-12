# Contributing to Peregrine

Thank you for your interest in contributing!

## How to Contribute

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Commit your changes with clear messages
4. Submit a Pull Request

## Coding Standards

- **C++**: C++17, clang-format
- **Python**: PEP 8, black
- **ROS 2**: follow rclcpp / rclpy best practices

## Areas of Contribution

- VIO integration (OpenVINS / ORB-SLAM3 ROS 2 wrappers)
- Visual Place Recognition (SuperPoint/SuperGlue, NetVLAD, etc.)
- EKF tuning and observability analysis
- Simulation tooling (AirSim scripts, data collection pipelines)
- Jetson deployment optimization (TensorRT, quantization)
- Real-world dataset collection and sim-to-real transfer

## PR Guidelines

- Keep changes scoped — one feature or bug fix per PR
- Update launch/config docs if interfaces change
- Update `README.md` if public APIs or dependencies change
