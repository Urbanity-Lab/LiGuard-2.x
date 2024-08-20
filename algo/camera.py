# contains the image processing algorithms

import numpy as np
from gui.logger_gui import Logger

def project_point_cloud_points(data_dict: dict, cfg_dict: dict):
    """
    Projects the points from a point cloud onto an image.

    Args:
        data_dict (dict): A dictionary containing the required data.
        cfg_dict (dict): A dictionary containing configuration parameters.

    Returns:
        None
    """
    if 'logger' in data_dict: logger:Logger = data_dict['logger']
    else: print('[algo->camera.py->project_point_cloud_points]: No logger object in data_dict. It is abnormal behavior as logger object is created by default. Please check if some script is removing the logger key in data_dict.'); return
    
    # Check if required data is present in data_dict
    if "current_point_cloud_numpy" not in data_dict:
        logger.log('[algo->camera.py->project_point_cloud_points]: current_point_cloud_numpy not found in data_dict', Logger.ERROR)
        return
    
    if "current_image_numpy" not in data_dict:
        logger.log('[alog->camera.py->project_point_cloud_points]: current_image_numpy not found in data_dict', Logger.ERROR)
        return
    
    if 'current_calib_data' not in data_dict:
        logger.log('[algo->camera.pyproject_point_cloud_points]: current_calib_data not found in data_dict', Logger.ERROR)
        return
    
    # Extract required calibration data
    Tr_velo_to_cam = data_dict['current_calib_data']['Tr_velo_to_cam']
    
    if 'R0_rect' in data_dict['current_calib_data']:
        R0_rect = data_dict['current_calib_data']['R0_rect']
    else:
        R0_rect = np.eye(4,4)
    
    P2 = data_dict['current_calib_data']['P2']
    
    # Convert lidar coordinates to homogeneous coordinates
    lidar_coords_Nx4 = np.hstack((data_dict['current_point_cloud_numpy'][:,:3], np.ones((data_dict['current_point_cloud_numpy'].shape[0], 1))))
    
    # Project lidar points onto the image plane
    pixel_coords = P2 @ R0_rect @ Tr_velo_to_cam @ lidar_coords_Nx4.T
    
    # Compute lidar depths
    lidar_depths = np.linalg.norm(lidar_coords_Nx4[:, :3], axis=1)
    
    # Filter out points that are behind the camera
    front_pixel_coords = pixel_coords[:, pixel_coords[2] > 0]
    front_lidar_depths = lidar_depths[pixel_coords[2] > 0]
    
    # Normalize pixel coordinates
    front_pixel_coords = front_pixel_coords[:2] / front_pixel_coords[2]
    front_pixel_coords = front_pixel_coords.T
    
    # Adjust lidar depths for visualization
    front_lidar_depths = front_lidar_depths * 6.0
    front_lidar_depths = 255.0 - np.clip(front_lidar_depths, 0, 255)
    
    # Convert pixel coordinates and lidar depths to the appropriate data types
    front_pixel_coords = front_pixel_coords.astype(int)
    front_lidar_depths = front_lidar_depths.astype(np.uint8)
    
    # Filter out coordinates that are outside the image boundaries
    valid_coords = (front_pixel_coords[:, 0] >= 0) & (front_pixel_coords[:, 0] < data_dict['current_image_numpy'].shape[1]) & (front_pixel_coords[:, 1] >= 0) & (front_pixel_coords[:, 1] < data_dict['current_image_numpy'].shape[0])
    
    # Select valid pixel coordinates and corresponding lidar depths
    pixel_coords_valid = front_pixel_coords[valid_coords]
    pixel_depths_valid = front_lidar_depths[valid_coords]
    
    # Update the image with the projected lidar points
    data_dict['current_image_numpy'][pixel_coords_valid[:, 1], pixel_coords_valid[:, 0]] = np.column_stack((pixel_depths_valid, np.zeros_like(pixel_depths_valid), np.zeros_like(pixel_depths_valid)))

def ultralytics_yolov5(data_dict: dict, cfg_dict: dict):
    """
    Runs the Ultralytics YOLOv5 object detection algorithm on the current image.

    Args:
        data_dict (dict): A dictionary containing the required data.
        cfg_dict (dict): A dictionary containing configuration parameters.

    Returns:
        None
    """
    if 'logger' in data_dict: logger:Logger = data_dict['logger']
    else: print('[algo->camera.py->ultralytics_yolov5]: No logger object in data_dict. It is abnormal behavior as logger object is created by default. Please check if some script is removing the logger key in data_dict.'); return
    
    if 'current_image_numpy' not in data_dict:
        logger.log('[algo->camera.py->ultralytics_yolov5]: current_image_numpy not found in data_dict', Logger.ERROR)
        return
    
    # imports
    import torch

    # algo name and keys used in algo
    algo_name = 'ultralytics_yolov5'
    model_key = f'{algo_name}_model'
    tgt_cls_key = f'{algo_name}_target_classes'
    
    # get params
    params = cfg_dict['proc']['camera']['ultralytics_yolov5']

    # check if model is already loaded
    if model_key not in data_dict:
        logger.log(f'[algo->camera.py->ultralytics_yolov5]: Loading model', Logger.INFO)
        data_dict[model_key] = torch.hub.load('ultralytics/yolov5', params['model'], pretrained=True, _verbose=False)
        vk_dict = {v.capitalize():k for (k,v) in data_dict[model_key].names.items()}
        data_dict[tgt_cls_key] = [vk_dict[key] for key in params['class_colors']]
    else:
        result = data_dict[model_key](data_dict['current_image_path']).xywh[0].detach().cpu().numpy()
        xywh = result[:, :4].astype(int)
        score = result[:, 4]
        obj_class = result[:, 5].astype(int)

        idx = np.argwhere(np.isin(obj_class, data_dict[tgt_cls_key]))
        
        xywh = xywh[idx].reshape(-1, 4)
        score = score[idx].reshape(-1)
        obj_class = obj_class[idx].reshape(-1)

        idx = np.argwhere(score >= params['score_threshold'])

        xywh = xywh[idx]
        score = score[idx]
        obj_class = obj_class[idx]

        for topleft_botright, cls in zip(xywh, obj_class):
            topleft_botright = topleft_botright.reshape(-1)
            obj_class_str = data_dict[model_key].names[cls.item()].capitalize()
            xy_center = topleft_botright[:2]
            xy_extent = topleft_botright[2:]
            rgb_color = np.array(params['class_colors'][obj_class_str], dtype=np.float32)
            bbox_2d = {'xy_center':xy_center, 'xy_extent':xy_extent, 'rgb_color':rgb_color, 'predicted':True, 'algo':algo_name}
            if 'current_label_list' not in data_dict: data_dict['current_label_list'] = []
            label = {'class': obj_class_str, 'bbox_2d':bbox_2d}
            data_dict['current_label_list'].append(label)

            


    
