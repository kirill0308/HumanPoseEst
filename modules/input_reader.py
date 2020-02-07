import cv2
import pyrealsense2 as rs
import numpy as np

class ImageReader:
    def __init__(self, file_names):
        self.file_names = file_names
        self.max_idx = len(file_names)

    def __iter__(self):
        self.idx = 0
        return self

    def __next__(self):
        if self.idx == self.max_idx:
            raise StopIteration
        img = cv2.imread(self.file_names[self.idx], cv2.IMREAD_COLOR)
        if img.size == 0:
            raise IOError('Image {} cannot be read'.format(self.file_names[self.idx]))
        self.idx = self.idx + 1
        return img


class VideoReader:
    def __init__(self, file_name):
        self.file_name = file_name
        try:  # OpenCV needs int to read from webcam
            self.file_name = int(file_name)
        except ValueError:
            pass

    def __iter__(self):
        self.cap = cv2.VideoCapture(self.file_name)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        if not self.cap.isOpened():
            raise IOError('Video {} cannot be opened'.format(self.file_name))
        return self

    def __next__(self):
        was_read, img = self.cap.read()
        if not was_read:
            raise StopIteration
        return img

class VideoReaderFromIntelRealsenseCAM:
    def __init__(self, frame_width, frame_height, CAM_FPS):
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, frame_width, frame_height, rs.format.z16, CAM_FPS)
        config.enable_stream(rs.stream.color, frame_width, frame_height, rs.format.bgr8, CAM_FPS)

        # color_path = 'temp/V00P00A00C00_rgb.avi'
        # depth_path = 'temp/V00P00A00C00_depth.avi'
        # colorwriter = cv2.VideoWriter(color_path, cv2.VideoWriter_fourcc(*'XVID'), CAM_FPS, (frame_width, frame_height),
        #                               1)
        # depthwriter = cv2.VideoWriter(depth_path, cv2.VideoWriter_fourcc(*'XVID'), CAM_FPS, (frame_width, frame_height),
        #                               1)
        self.pipeline.start(config)

    def __iter__(self):
        self.frames = self.pipeline.wait_for_frames()
        return self

    def __next__(self):
        # depth_frame = self.frames.get_depth_frame()
        color_frame = self.frames.get_color_frame()
        if not color_frame:
            raise StopIteration
        color_image = np.asanyarray(color_frame.get_data())
        return color_image
