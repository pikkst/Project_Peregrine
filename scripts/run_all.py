#!/usr/bin/env python3
"""
run_all.py - Main script to start the Peregrine system

This script:
1. Checks the ROS2 environment
2. Builds the workspace if needed
3. Starts Unreal + AirSim (if available)
4. Launches the ROS2 system
5. Provides monitoring options

Usage: python3 run_all.py [options]
"""

import os
import sys
import subprocess
import time
import argparse
import signal
import threading
from pathlib import Path

# Constants
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
ROS2_WS = PROJECT_ROOT / "ros2_ws"
UNREAL_PROJECT = PROJECT_ROOT / "UnrealProjects" / "PeregrineSimulation"
AIRSIM_CONFIG = PROJECT_ROOT / "AirSim" / "settings.json"

def check_ros2_environment():
    """Check if ROS2 environment is properly sourced."""
    print("=" * 60)
    print("Checking ROS2 environment...")
    print("=" * 60)

    # Check for ROS2 installation
    try:
        result = subprocess.run(
            ["where", "ros2"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("❌ Error: ROS2 not found in PATH")
            print("   Please source your ROS2 setup script:")
            print("   call C:\\opt\\ros\\humble\\setup.bash")
            return False
        print(f"✅ ROS2 found: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Error checking ROS2: {e}")
        return False

    # Check for colcon
    try:
        result = subprocess.run(
            ["where", "colcon"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("❌ Error: colcon not found in PATH")
            return False
        print(f"✅ Colcon found: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Error checking colcon: {e}")
        return False

    # Check ROS2 version
    try:
        result = subprocess.run(
            ["ros2", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ ROS2 version: {result.stdout.strip()}")
    except Exception as e:
        print(f"⚠️  Warning: Could not get ROS2 version: {e}")

    print("✅ ROS2 environment check passed\n")
    return True

def build_workspace(force_build=False):
    """Build the ROS2 workspace if needed."""
    print("=" * 60)
    print("Checking workspace build status...")
    print("=" * 60)

    build_dir = ROS2_WS / "build"
    install_dir = ROS2_WS / "install"

    needs_build = force_build or not install_dir.exists()

    if not needs_build:
        # Check if any source files were modified
        try:
            build_time = install_dir.stat().st_mtime
            for root, dirs, files in os.walk(ROS2_WS / "src"):
                for file in files:
                    if file.endswith((".py", ".cpp", ".hpp", ".xml")):
                        file_path = Path(root) / file
                        if file_path.stat().st_mtime > build_time:
                            needs_build = True
                            print(f"   Detected changes in {file_path.relative_to(ROS2_WS)}")
                            break
                if needs_build:
                    break
        except Exception as e:
            print(f"⚠️  Could not check file modification times: {e}")
            needs_build = True

    if needs_build:
        print("📦 Building workspace...")
        print("-" * 60)

        try:
            # Run colcon build
            result = subprocess.run(
                ["colcon", "build", "--symlink-install"],
                cwd=ROS2_WS,
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                print("✅ Build completed successfully!")
                # Source the setup file
                setup_file = install_dir / "local_setup.sh"
                if setup_file.exists():
                    source_cmd = f"call {setup_file}"
                    print(f"   Run this to update your environment:\n   {source_cmd}")
            else:
                print(f"❌ Build failed with exit code {result.returncode}")
                print("\nBuild output:")
                print(result.stdout)
                print("\nBuild errors:")
                print(result.stderr)
                return False

        except subprocess.TimeoutExpired:
            print("❌ Build timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"❌ Build error: {e}")
            return False
    else:
        print("✅ Workspace already built, skipping build step")

    print()
    return True

def start_unreal_airsim():
    """Start Unreal Engine and AirSim if available."""
    print("=" * 60)
    print("Checking Unreal + AirSim...")
    print("=" * 60)

    # Check if Unreal project exists
    if not UNREAL_PROJECT.exists():
        print(f"⚠️  Unreal project not found at {UNREAL_PROJECT}")
        print("   Skipping simulation startup")
        print("   (Set use_sim_time:=false when launching)")
        return None

    # Check for AirSim config
    if not AIRSIM_CONFIG.exists():
        print(f"⚠️  AirSim config not found at {AIRSIM_CONFIG}")
        print("   You may need to configure AirSim")

    print(f"📍 Unreal project: {UNREAL_PROJECT}")
    print(f"📍 AirSim config: {AIRSIM_CONFIG}")

    choice = input("\nStart Unreal + AirSim? [y/N]: ").strip().lower()
    if choice not in ['y', 'yes']:
        print("⏭️  Skipping simulation startup")
        return None

    print("🚀 Starting simulation...")
    print("-" * 60)

    try:
        # Note: This is a simplified example
        # In practice, you'd need the full path to Unreal Engine
        print("   Please start Unreal manually if needed")
        print("   Command: UE4Editor \"C:/.../PeregrineSimulation.uproject\" -game")

        # Start AirSim
        try:
            airsim_process = subprocess.Popen(
                ["python", "-m", "airsim"],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"✅ AirSim started (PID: {airsim_process.pid})")
            return airsim_process
        except Exception as e:
            print(f"⚠️  Could not start AirSim automatically: {e}")
            print("   Please start AirSim manually")

    except Exception as e:
        print(f"⚠️  Could not start simulation: {e}")

    return None

def launch_ros2_system(use_sim_time=False):
    """Launch the ROS2 system."""
    print("=" * 60)
    print("Launching ROS2 system...")
    print("=" * 60)

    launch_file = ROS2_WS / "src" / "peregrine_launch" / "launch" / "peregrine_all.launch.py"

    if not launch_file.exists():
        print(f"❌ Launch file not found: {launch_file}")
        return None

    print(f"📍 Launch file: {launch_file}")

    print(f"\n🚀 Starting launch...")
    print("-" * 60)

    try:
        cmd = ["ros2", "launch", str(launch_file)]
        if use_sim_time:
            cmd.append("use_sim_time:=true")

        print(f"   Command: {' '.join(cmd)}")
        print()

        process = subprocess.Popen(
            cmd,
            cwd=ROS2_WS,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Start a thread to read output
        def read_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"   [ROS2] {line.strip()}")

        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()

        print(f"✅ ROS2 system launched (PID: {process.pid})")
        print()
        return process

    except Exception as e:
        print(f"❌ Failed to launch ROS2 system: {e}")
        return None

def monitor_system(ros2_process):
    """Provide monitoring options for the running system."""
    print("=" * 60)
    print("System Monitoring")
    print("=" * 60)
    print()
    print("Available commands:")
    print("  1. List topics")
    print("  2. Show topic info")
    print("  3. Monitor specific topic")
    print("  4. Show nodes")
    print("  5. Show node info")
    print("  6. Show parameters")
    print("  7. View diagnostics")
    print("  8. Launch rqt (if available)")
    print("  9. Launch rviz2 (if available)")
    print("  q. Quit monitoring")
    print()

    while True:
        if ros2_process and ros2_process.poll() is not None:
            print("\n❌ ROS2 process has terminated")
            break

        try:
            cmd = input("> ").strip().lower()

            if cmd == 'q':
                break
            elif cmd == '1':
                subprocess.run(["ros2", "topic", "list"], timeout=10)
            elif cmd == '2':
                topic = input("   Enter topic name: ").strip()
                if topic:
                    subprocess.run(["ros2", "topic", "info", topic], timeout=10)
            elif cmd == '3':
                topic = input("   Enter topic name: ").strip()
                if topic:
                    subprocess.run(["ros2", "topic", "echo", topic], timeout=10)
            elif cmd == '4':
                subprocess.run(["ros2", "node", "list"], timeout=10)
            elif cmd == '5':
                node = input("   Enter node name: ").strip()
                if node:
                    subprocess.run(["ros2", "node", "info", node], timeout=10)
            elif cmd == '6':
                node = input("   Enter node name: ").strip()
                if node:
                    subprocess.run(["ros2", "param", "list", node], timeout=10)
            elif cmd == '7':
                subprocess.run(["ros2", "diagnostics"], timeout=10)
            elif cmd == '8':
                try:
                    subprocess.Popen(["rqt"], start_new_session=True)
                    print("   Started rqt")
                except:
                    print("   ❌ rqt not available")
            elif cmd == '9':
                try:
                    subprocess.Popen(["rviz2"], start_new_session=True)
                    print("   Started rviz2")
                except:
                    print("   ❌ rviz2 not available")
            else:
                print("   Unknown command")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"   Error: {e}")

def cleanup(airsim_process, ros2_process):
    """Clean up processes."""
    print("\n" + "=" * 60)
    print("Cleaning up...")
    print("=" * 60)

    if ros2_process:
        print("Stopping ROS2 system...")
        ros2_process.terminate()
        try:
            ros2_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("Force killing ROS2 process...")
            ros2_process.kill()

    if airsim_process:
        print("Stopping AirSim...")
        airsim_process.terminate()
        try:
            airsim_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("Force killing AirSim process...")
            airsim_process.kill()

    print("✅ Cleanup complete")

def main():
    """Main function."""
    print()
    print("=" * 60)
    print("  Peregrine System - Run All")
    print("=" * 60)
    print()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Start the Peregrine system"
    )
    parser.add_argument(
        '--force-build',
        action='store_true',
        help='Force rebuild the workspace'
    )
    parser.add_argument(
        '--skip-ros-check',
        action='store_true',
        help='Skip ROS2 environment check'
    )
    parser.add_argument(
        '--no-sim',
        action='store_true',
        help='Skip starting simulation'
    )
    parser.add_argument(
        '--sim-time',
        action='store_true',
        help='Use simulation time'
    )
    args = parser.parse_args()

    airsim_process = None
    ros2_process = None

    try:
        # Step 1: Check ROS2 environment
        if not args.skip_ros_check:
            if not check_ros2_environment():
                print("\n❌ Cannot continue without ROS2 environment")
                sys.exit(1)
        else:
            print("⏭️  Skipping ROS2 environment check")

        # Step 2: Build workspace if needed
        if not build_workspace(force_build=args.force_build):
            print("\n❌ Build failed, cannot continue")
            sys.exit(1)

        # Step 3: Source the workspace
        print("=" * 60)
        print("Sourcing workspace...")
        print("=" * 60)
        setup_file = ROS2_WS / "install" / "setup.sh"
        if setup_file.exists():
            source_cmd = f"source {setup_file} && echo 'Sourced successfully'"
            result = subprocess.run(
                ["bash", "-c", source_cmd],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Workspace sourced")
            else:
                print("⚠️  Could not source workspace automatically")
                print("   Please run: source install/setup.bash")
        print()

        # Step 4: Start Unreal + AirSim (optional)
        if not args.no_sim:
            airsim_process = start_unreal_airsim()
            if airsim_process:
                print("⏳ Waiting for AirSim to initialize...")
                time.sleep(5)

        # Step 5: Launch ROS2 system
        ros2_process = launch_ros2_system(use_sim_time=args.sim_time)
        if not ros2_process:
            print("\n❌ Failed to launch ROS2 system")
            cleanup(airsim_process, None)
            sys.exit(1)

        # Step 6: Provide monitoring options
        print("\n" + "=" * 60)
        print("✅ System is running!")
        print("=" * 60)
        print()
        print("Press Ctrl+C to enter monitoring menu")
        print("-" * 60)

        # Wait a bit, then offer monitoring
        time.sleep(3)

        try:
            monitor_system(ros2_process)
        except KeyboardInterrupt:
            pass

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        cleanup(airsim_process, ros2_process)

    print("\n👋 Goodbye!\n")

if __name__ == "__main__":
    main()