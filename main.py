from argparse import ArgumentParser
import json
import os
import time

import cv2
import numpy as np
import socket
import configparser
import imutils

from modules.input_reader import VideoReader, ImageReader, VideoReaderFromIntelRealsenseCAM
from modules.draw import Plotter3d, draw_poses
from modules.parse_poses import parse_poses


def rotate_poses(poses_3d, R, t):
    R_inv = np.linalg.inv(R)
    for pose_id in range(len(poses_3d)):
        pose_3d = poses_3d[pose_id].reshape((-1, 4)).transpose()
        pose_3d[0:3, :] = np.dot(R_inv, pose_3d[0:3, :] - t)
        poses_3d[pose_id] = pose_3d.transpose().reshape(-1)

    return poses_3d


if __name__ == '__main__':
    parser = ArgumentParser(description='Lightweight 3D human pose estimation demo. '
                                        'Press esc to exit, "p" to (un)pause video or process next image.')
    parser.add_argument('-m', '--model',
                        help='Required. Path to checkpoint with a trained model '
                             '(or an .xml file in case of OpenVINO inference).',
                        type=str, required=True)
    parser.add_argument('--use-intelrealsensecamera', help='Optional. Use intel realsense camera.', action='store_true')
    parser.add_argument('--video', help='Optional. Path to video file or camera id.', type=str, default='')
    parser.add_argument('-d', '--device',
                        help='Optional. Specify the target device to infer on: CPU or GPU. '
                             'The demo will look for a suitable plugin for device specified '
                             '(by default, it is GPU).',
                        type=str, default='GPU')
    parser.add_argument('--use-openvino',
                        help='Optional. Run network with OpenVINO as inference engine. '
                             'CPU, GPU, FPGA, HDDL or MYRIAD devices are supported.',
                        action='store_true')
    parser.add_argument('--rotation-to-vertical',
                        help='Optional. rotate camera from horizontal to vertical',
                        action='store_true')
    parser.add_argument('--images', help='Optional. Path to input image(s).', nargs='+', default='')
    parser.add_argument('--height-size', help='Optional. Network input layer height size.', type=int, default=256)
    parser.add_argument('--extrinsics-path',
                        help='Optional. Path to file with camera extrinsics.',
                        type=str, default=None)
    parser.add_argument('--fx', type=np.float32, default=-1, help='Optional. Camera focal length.')
    args = parser.parse_args()

    # read setting info from ini file
    try:
        # Camera info
        config = configparser.ConfigParser()
        config.read('setting.ini')
        frame_width = int(config['CAMERA']['Width'])
        frame_height = int(config['CAMERA']['Height'])
        CAM_FPS = int(config['CAMERA']['FPS'])
        # TCP/IP Socket info
        TCP_IP = config['SOCKET']['TCP_IP']
        TCP_PORT = int(config['SOCKET']['TCP_PORT'])
    except:
        # Camera info
        frame_width = 640
        frame_height = 480
        CAM_FPS = 30
        # TCP/IP Socket info
        TCP_IP = '127.0.0.1'
        TCP_PORT = 5005


    if args.video == '' and args.images == '':
        raise ValueError('Either --video or --image has to be provided')

    stride = 8
    if args.use_openvino:
        from modules.inference_engine_openvino import InferenceEngineOpenVINO
        net = InferenceEngineOpenVINO(args.model, args.device)
    else:
        from modules.inference_engine_pytorch import InferenceEnginePyTorch
        net = InferenceEnginePyTorch(args.model, args.device)

    canvas_3d = np.zeros((720, 1280, 3), dtype=np.uint8)
    plotter = Plotter3d(canvas_3d.shape[:2])
    canvas_3d_window_name = 'Canvas 3D'
    cv2.namedWindow(canvas_3d_window_name)
    cv2.setMouseCallback(canvas_3d_window_name, Plotter3d.mouse_callback)

    file_path = args.extrinsics_path
    if file_path is None:
        file_path = os.path.join('data', 'extrinsics.json')
    with open(file_path, 'r') as f:
        extrinsics = json.load(f)
    R = np.array(extrinsics['R'], dtype=np.float32)
    t = np.array(extrinsics['t'], dtype=np.float32)

    frame_provider = ImageReader(args.images)
    is_video = False
    if args.use_intelrealsensecamera:
        frame_provider = VideoReaderFromIntelRealsenseCAM(frame_width, frame_height, CAM_FPS)
        is_video = True
    elif args.video != '':
        frame_provider = VideoReader(args.video)
        is_video = True
    base_height = args.height_size
    fx = args.fx

    delay = 1
    esc_code = 27
    p_code = 112
    space_code = 32
    mean_time = 0
    for frame in frame_provider:
        current_time = cv2.getTickCount()
        if frame is None:
            break

        # check if ratation to vertical
        if args.rotation_to_vertical:
            # frame = np.rot90(frame, k=-1, axes=(0, 1))
            frame = imutils.rotate_bound(frame, 90)

        input_scale = base_height / frame.shape[0]
        scaled_img = cv2.resize(frame, dsize=None, fx=input_scale, fy=input_scale)
        scaled_img = scaled_img[:, 0:scaled_img.shape[1] - (scaled_img.shape[1] % stride)]  # better to pad, but cut out for demo
        if fx < 0:  # Focal length is unknown
            fx = np.float32(0.8 * frame.shape[1])

        inference_result = net.infer(scaled_img)
        poses_3d, poses_2d = parse_poses(inference_result, input_scale, stride, fx, is_video)
        edges = []
        if len(poses_3d):
            poses_3d = rotate_poses(poses_3d, R, t)
            poses_3d_copy = poses_3d.copy()
            x = poses_3d_copy[:, 0::4]
            y = poses_3d_copy[:, 1::4]
            z = poses_3d_copy[:, 2::4]
            # poses_3d[:, 0::4], poses_3d[:, 1::4], poses_3d[:, 2::4] = -z, x, -y
            poses_3d[:, 0::4], poses_3d[:, 1::4], poses_3d[:, 2::4] = -z, x, -y

            poses_3d = poses_3d.reshape(poses_3d.shape[0], 19, -1)[:, :, 0:3]
            edges = (Plotter3d.SKELETON_EDGES + 19 * np.arange(poses_3d.shape[0]).reshape((-1, 1, 1))).reshape((-1, 2))
            edgesForUnity = (Plotter3d.SKELETON_EDGES_FOR_UNITY + 19 * np.arange(poses_3d.shape[0]).reshape((-1, 1, 1))).reshape((-1, 2))
            ################### send pos 3D data to Unity ################
            # convert vetices to bones position to use in Unity3D
            poses_3d_edges_for_unity = poses_3d.reshape((-1, 3))[edgesForUnity]
            poses_3d_edges_for_unity = (poses_3d_edges_for_unity[:, 0:1] + poses_3d_edges_for_unity[:, 1:2]) / 2
            # Spine
            poses_3d_edges_for_unity[7][0] = (poses_3d_edges_for_unity[0][0] + poses_3d_edges_for_unity[7][0]) / 2
            # Head
            poses_3d_edges_for_unity[10][0] = poses_3d_edges_for_unity[9][0] + (poses_3d_edges_for_unity[10][0] - poses_3d_edges_for_unity[9][0])*2

            # send now
            array = []
            for j in range(17):
                # array.extend([xNew[0][j], yNew[0][j], zNew[0][j]])
                array.extend(poses_3d_edges_for_unity[j][0])
            array = " ".join(str(x) for x in array)

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((TCP_IP, TCP_PORT))
                s.sendall(bytes(array, encoding='utf-8'))
                s.close()
                # print(array)
            except:
                pass

            # append to file
            # f = open("pos_sample_socket1.txt", "a+")
            # f.write(array + "\r\n")
            # f.close()
            #####################################################

        #plotter.plot(canvas_3d, poses_3d, edges)
        #cv2.imshow(canvas_3d_window_name, canvas_3d)


        draw_poses(frame, poses_2d)
        current_time = (cv2.getTickCount() - current_time) / cv2.getTickFrequency()
        if mean_time == 0:
            mean_time = current_time
        else:
            mean_time = mean_time * 0.95 + current_time * 0.05
        cv2.putText(frame, 'FPS: {}'.format(int(1 / mean_time * 10) / 10),
                    (40, 80), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255))
        cv2.imshow('ICV 3D Human Pose Estimation', frame)

        key = cv2.waitKey(delay)
        if key == esc_code:
            break
        if key == p_code:
            if delay == 1:
                delay = 0
            else:
                delay = 1
        if delay == 0 or not is_video:  # allow to rotate 3D canvas while on pause
            key = 0
            while (key != p_code
                   and key != esc_code
                   and key != space_code):
                plotter.plot(canvas_3d, poses_3d, edges)
                cv2.imshow(canvas_3d_window_name, canvas_3d)
                key = cv2.waitKey(33)
            if key == esc_code:
                break
            else:
                delay = 1

    if args.use_intelrealsensecamera:
        try:
            frame_provider.pipeline.stop()
        except:
            pass
