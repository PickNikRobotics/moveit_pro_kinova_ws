cmake_minimum_required(VERSION 3.5)
project(zed_description)

# find dependencies
find_package(ament_cmake REQUIRED)


install(
        DIRECTORY launch urdf rviz
        DESTINATION share/zed_description
)


ament_package()
