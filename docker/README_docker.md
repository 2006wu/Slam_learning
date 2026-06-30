# TurtleBot Docker environment

ROS 2 Jazzy development environment for implementing 2D SLAM from scratch. It
contains TurtleBot3 Gazebo, RViz and build tools, but no Nav2 or third-party SLAM
package.

- ROS domain ID: `77`
- RMW: CycloneDDS
- VNC port: `7778`
- Default VNC password: `ros`
- Default TurtleBot3 model: `burger`

## VNC desktop (recommended)

From the `TurtleBot/docker` directory:

```bash
docker compose up --build -d turtlebot-vnc
docker compose exec turtlebot-vnc bash
```

Connect a VNC client to `localhost:7778`. GUI commands run from the attached shell
will appear on the XFCE desktop:

```bash
rviz2
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

Stop the environment:

```bash
docker compose down
```

## Development shell without VNC

```bash
docker compose run --rm turtlebot-develop
```

The project root is mounted at `/home/user/TurtleBot`.

## Common commands

```bash
# Build the workspace
colcon build --symlink-install

# Drive with this repository's keyboard node
source install/setup.bash
ros2 run turtlebot_keyboard keyboard_controller

# Record deterministic SLAM input
ros2 bag record -o bags/turtlebot3_world /scan /odom /tf /tf_static /clock
```

Override optional settings when starting Compose:

```bash
TURTLEBOT3_MODEL=waffle VNC_PASSWORD=change-me \
VNC_RESOLUTION=1920x1080 docker compose up -d turtlebot-vnc
```

`turtlebot-develop` uses host networking for ROS 2 discovery. The VNC service uses
a published port so it also works with Docker Desktop on macOS.
