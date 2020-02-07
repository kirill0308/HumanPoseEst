import pyrealsense2 as rs
import numpy as np
import cv2
import configparser

try:
    config = configparser.ConfigParser()
    config.read('setting.ini')
    frame_width = int(config['CAMERA']['Width'])
    frame_height = int(config['CAMERA']['Height'])
    CAM_FPS = int(config['CAMERA']['FPS'])
except:
    frame_width = 640
    frame_height = 480
    CAM_FPS = 30

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, frame_width, frame_height, rs.format.z16, CAM_FPS)
config.enable_stream(rs.stream.color, frame_width, frame_height, rs.format.bgr8, CAM_FPS)

color_path = 'temp/V00P00A00C00_rgb.avi'
depth_path = 'temp/V00P00A00C00_depth.avi'
colorwriter = cv2.VideoWriter(color_path, cv2.VideoWriter_fourcc(*'XVID'), CAM_FPS, (frame_width, frame_height), 1)
depthwriter = cv2.VideoWriter(depth_path, cv2.VideoWriter_fourcc(*'XVID'), CAM_FPS, (frame_width, frame_height), 1)

pipeline.start(config)

try:
    while True:
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

        colorwriter.write(color_image)
        depthwriter.write(depth_colormap)

        cv2.imshow('Stream', depth_colormap)

        if cv2.waitKey(1) == ord("q"):
            break
finally:
    colorwriter.release()
    depthwriter.release()
    pipeline.stop()