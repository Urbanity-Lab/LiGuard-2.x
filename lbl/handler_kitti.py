import os
import numpy as np

colors = {
    'Car': [0, 1, 0],
    'Van': [0, 1, 0],
    'Truck': [0, 1, 0],
    'Pedestrian': [1, 0, 0],
    'Person_sitting': [1, 0, 0],
    'Cyclist': [0, 0, 1],
    'Tram': [1, 1, 0],
    'Misc': [1, 1, 0],
    'DontCare': [1, 1, 1]
}
label_file_extension = '.txt'
calib_file_extension = '.txt'

def Handler(label_path: str, calib_path: str):
    output = []
    
    # read calib
    calib = __read_calib__(calib_path)
    
    # must be P2[3x4] @ R0_rect[4x4] @ Tr_velo_to_cam[4x4] -> 3x4
    calib['P2'] = calib['P2'].reshape(3, 4) # 3x4
    
    calib['R0_rect'] = calib['R0_rect'].reshape(3, 3) # 3x3
    calib['R0_rect'] = np.pad(calib['R0_rect'], ((0, 1), (0, 1)), mode='constant', constant_values=0) # 4x4
    calib['R0_rect'][3, 3] = 1
    
    calib['Tr_velo_to_cam'] = calib['Tr_velo_to_cam'].reshape(3, 4) # 3x4
    calib['Tr_velo_to_cam'] = np.vstack((calib['Tr_velo_to_cam'], np.array([0,0,0,1], dtype=np.float32))) # 4x4
    
    transform_from_lidar_to_image_0 = calib['Tr_velo_to_cam']
    transform_from_image_0_to_image_2 = calib['P2']
    transform_from_image_0_to_lidar = np.linalg.inv(transform_from_lidar_to_image_0)
    
    # read label file
    if os.path.exists(label_path) == False: return output
    with open(label_path, 'r') as f: lbls = f.readlines()
    for line in lbls:
        parts = line.strip().split(' ')
        obj_class = parts[0] # object class [Car, Van, Truck, Pedestrian, Person_sitting, Cyclist, Tram, Misc, DontCare]
        truncation = float(parts[1]) # truncated pixel ratio [0..1]
        occlusion = int(parts[2]) # 0: fully visible, 1: partly occluded, 2: fully occluded, 3: unknown
        alpha = float(parts[3]) # object observation angle [-pi..pi]
        left, top, right, bottom = np.array([float(x) for x in parts[4:8]], dtype=np.float32) # 0-based 2D bounding box of object in the image
        height, width, length = np.array([float(x) for x in parts[8:11]], dtype=np.float32) # height, width, length in meters
        image_0_xyz = np.array([float(x) for x in parts[11:14]], dtype=np.float32) # location of object center in camera coordinates
        image_0_ry = float(parts[14]) # rotation around Y-axis in camera coordinates [-pi..pi]
        
        label = dict()
        label['class'] = obj_class
        label['truncation'] = truncation
        label['occlusion'] = occlusion
        label['alpha'] = alpha
        label['image_0_bbox2d'] = [left, top, right, bottom]
        label['obj_height'] = height
        label['obj_width'] = width
        label['obj_length'] = length
        label['image_0_xyz'] = image_0_xyz
        label['image_0_ry'] = image_0_ry
        
        lidar_xyz_center = transform_from_image_0_to_lidar @ np.append(image_0_xyz, 1).reshape(4, 1)
        lidar_xyz_center = lidar_xyz_center.T[0]
        lidar_xyz_center = lidar_xyz_center[:3]
        lidar_xyz_center[2] += height / 2.0
        lidar_xyz_extent = np.array([width, length, height], dtype=np.float32)
        lidar_xyz_euler_angles = np.array([0, 0, -image_0_ry], dtype=np.float32)
        lidar_bbox_color = np.array(colors[obj_class], dtype=np.uint8)
        
        label['lidar_bbox'] = {'lidar_xyz_center': lidar_xyz_center, 'lidar_xyz_extent': lidar_xyz_extent, 'lidar_xyz_euler_angles': lidar_xyz_euler_angles, 'rgb_bbox_color': lidar_bbox_color, 'predicted': False}
        
        camera_bbox_color = np.array([i * 255.0 for i in colors[obj_class]], dtype=np.uint8)
        
        label['camera_bbox'] = {'lidar_xyz_center': lidar_xyz_center, 'lidar_xyz_extent': lidar_xyz_extent, 'lidar_xyz_euler_angles': lidar_xyz_euler_angles, 'rgb_bbox_color': camera_bbox_color, 'predicted': False}
        
        output.append(label)
    
    return output, calib

def __read_calib__(calib_path: str):
    calib = {}
    with open(calib_path) as f:
        for line in f.readlines():
            line = line.strip()
            if len(line) == 0: continue
            k, v = line.split(':')
            calib[k] = np.array([float(x) for x in v.split()], dtype=np.float32)
    return calib