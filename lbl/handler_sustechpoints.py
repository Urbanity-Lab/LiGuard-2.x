import os
import numpy as np
import open3d as o3d
import json

colors = {
    "Car":            (0  ,255,0  ),#'#00ff00',
    "Van":            (0  ,255,0  ),#'#00ff00',
    "Bus":            (0  ,255,255),#'#ffff00', 
    "Pedestrian":     (0  ,0  ,255),#'#ff0000',
    "Rider":          (0  ,136,255),#'#ff8800',
    "Cyclist":        (0  ,136,255),#'#ff8800',
    "Bicycle":        (0  ,255,136),#'#88ff00',
    "BicycleGroup":   (0  ,255,136),#'#88ff00',
    "Motor":          (0  ,176,176),#'#aaaa00',
    "Truck":          (255,255,0  ),#'#00ffff',
    "Tram":           (255,255,0  ),#'#00ffff',
    "Animal":         (255,176,0  ),#'#00aaff',
    "Misc":           (136,136,0  ),#'#008888',
    "Unknown":        (136,136,0  ),#'#008888',
}
label_file_extension = '.json'
calib_file_extension = '.json'

def Handler(label_path: str, calib_path: str):
    output = []
    
    # read calib
    calib_file_name = os.path.basename(calib_path).split('.')[0]
    calib_path = calib_path.replace(calib_file_name, 'front') # front camera calib
    calib_exists = os.path.exists(calib_path)
    if calib_exists:
        with open(calib_path, 'r') as f: calib = json.load(f)
        extrinsic_matrix  = np.reshape(calib['extrinsic'], [4,4])
        intrinsic_matrix  = np.reshape(calib['intrinsic'], [3,3])

    # read label file
    if os.path.exists(label_path) == False: return output
    with open(label_path, 'r') as f: lbls = json.load(f)
    for item in lbls:
        annotator = item['annotator'] if 'annotator' in item else 'Unknown'
        obj_id = int(item['obj_id'])
        obj_type = item['obj_type']
        psr = item['psr']
        psr_position_xyz = np.array([psr['position']['x'], psr['position']['y'], psr['position']['z']], dtype=np.float64)
        psr_rotation_xyz = np.array([psr['rotation']['x'], psr['rotation']['y'], psr['rotation']['z']], dtype=np.float64)
        psr_scale_xyz = np.array([psr['scale']['x'], psr['scale']['y'], psr['scale']['z']], dtype=np.float64)
        
        label = dict()
        label['annotator'] = annotator
        label['id'] = obj_id
        label['type'] = obj_type
        label['psr'] = psr
        if calib_exists:
            label['calib'] = calib
            label['calib']['Tr_velo_to_cam'] = extrinsic_matrix
            label['calib']['P2'] = intrinsic_matrix
        
        lidar_xyz_center = psr_position_xyz.copy()
        lidar_xyz_extent = psr_scale_xyz.copy()
        lidar_xyz_euler_angles = psr_rotation_xyz.copy()

        if obj_type in colors: lidar_bbox_color = np.array([i / 255.0 for i in colors[obj_type]], dtype=np.uint8)
        else: lidar_bbox_color = np.array([0, 0, 0], dtype=np.uint8)
        
        label['lidar_bbox'] = {'lidar_xyz_center': lidar_xyz_center, 'lidar_xyz_extent': lidar_xyz_extent, 'lidar_xyz_euler_angles': lidar_xyz_euler_angles, 'rgb_bbox_color': lidar_bbox_color}
        
        if calib_exists:
            if obj_type in colors: camera_bbox_color = np.array(colors[obj_type], dtype=np.uint8)
            else: camera_bbox_color = np.array([0, 0, 0], dtype=np.uint8)
            label['camera_bbox'] = {'lidar_xyz_center': lidar_xyz_center, 'lidar_xyz_extent': lidar_xyz_extent, 'lidar_xyz_euler_angles': lidar_xyz_euler_angles, 'rgb_bbox_color': camera_bbox_color}
        
        output.append(label)
    
    return output