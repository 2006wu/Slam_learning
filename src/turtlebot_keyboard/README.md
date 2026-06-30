# turtlebot_keyboard

ROS 2 Jazzy keyboard controller for TurtleBot3. It publishes
`geometry_msgs/msg/TwistStamped` commands to `/cmd_vel` at 10 Hz.

## Build and run

```bash
cd /home/user/TurtleBot
colcon build --symlink-install --packages-select turtlebot_keyboard
source install/setup.bash
ros2 run turtlebot_keyboard keyboard_controller
```

Controls:

- `W` / `S`: move forward / backward at `0.01 m/s`
- `A` / `D`: rotate left / right at `0.01 rad/s`
- `Space` or `X`: stop
- `Ctrl-C`: stop and exit

The command continues until another movement or stop key is pressed.
