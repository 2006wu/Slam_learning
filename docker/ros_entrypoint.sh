#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-burger}"

exec "$@"
