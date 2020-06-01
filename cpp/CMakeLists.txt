cmake_minimum_required(VERSION 3.26)
project(Trader)

# Add the executable


file(GLOB_RECURSE SOURCE_FILES "*.cpp" "*.h")

add_executable(Trader Trader.cpp)

# Set include directories for the dependency library
target_include_directories(Trader PUBLIC ${PROJECT_SOURCE_DIR}/libs/ibapi_cpp/)
target_include_directories(Trader PUBLIC ${PROJECT_SOURCE_DIR}/libs/ibapi_cpp/lib)

# Link against the dependency library
target_link_libraries(Trader PUBLIC ${PROJECT_SOURCE_DIR}/libs/ibapi_cpp/build/libTwsSocketClient.a)
target_link_libraries(Trader PUBLIC ${PROJECT_SOURCE_DIR}/libs/ibapi_cpp/lib/gcc000blibbid.a)