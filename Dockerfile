FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        git \
        cmake \
        build-essential \
        libusb-1.0-0 \
        libglfw3-dev \
        libgtk-3-dev \
        && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/librealsense && \
    cd /root/librealsense && \
    git clone https://github.com/IntelRealSense/librealsense.git && \
    cd librealsense && \
    mkdir build && cd build && \
    cmake .. && \
    make -j4 && \
    make install && \
    ldconfig

EXPOSE 5000

CMD ["bash"]
