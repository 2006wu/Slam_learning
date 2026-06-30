FROM ros:jazzy-ros-base-noble

ARG USERNAME=user
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Taipei \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    ROS_DISTRO=jazzy \
    ROS_DOMAIN_ID=77 \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    TURTLEBOT3_MODEL=burger \
    DISPLAY=:1 \
    VNC_PORT=7778 \
    NOVNC_PORT=6080 \
    VNC_PASSWORD=ros \
    QT_X11_NO_MITSHM=1 \
    LIBGL_ALWAYS_SOFTWARE=1

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      cmake \
      dbus-x11 \
      libeigen3-dev \
      locales \
      novnc \
      python3-colcon-common-extensions \
      python3-rosdep \
      sudo \
      tigervnc-standalone-server \
      websockify \
      xfce4 \
      xfce4-terminal \
      x11-xserver-utils \
      ros-jazzy-rmw-cyclonedds-cpp \
      ros-jazzy-rviz2 \
      ros-jazzy-turtlebot3-gazebo \
    && locale-gen en_US.UTF-8 \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 packages tigervncpasswd separately from the VNC server.
RUN apt-get update && apt-get install -y --no-install-recommends \
      tigervnc-tools \
    && rm -rf /var/lib/apt/lists/*

RUN existing_group="$(getent group "${USER_GID}" | cut -d: -f1 || true)" \
    && if [[ -n "${existing_group}" && "${existing_group}" != "${USERNAME}" ]]; then \
         groupmod --new-name "${USERNAME}" "${existing_group}"; \
       elif [[ -z "${existing_group}" ]]; then \
         groupadd --gid "${USER_GID}" "${USERNAME}"; \
       fi \
    && existing_user="$(getent passwd "${USER_UID}" | cut -d: -f1 || true)" \
    && if [[ -n "${existing_user}" && "${existing_user}" != "${USERNAME}" ]]; then \
         usermod --login "${USERNAME}" --home "/home/${USERNAME}" --move-home "${existing_user}"; \
       elif [[ -z "${existing_user}" ]]; then \
         useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /bin/bash "${USERNAME}"; \
       fi \
    && usermod --gid "${USER_GID}" --shell /bin/bash "${USERNAME}" \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}"

COPY ros_entrypoint.sh /usr/local/bin/ros-entrypoint
COPY start_vnc.sh /usr/local/bin/start-vnc
RUN chmod +x /usr/local/bin/ros-entrypoint /usr/local/bin/start-vnc

USER ${USERNAME}
WORKDIR /home/${USERNAME}

EXPOSE 7778 6080

ENTRYPOINT ["/usr/local/bin/ros-entrypoint"]
CMD ["bash"]
