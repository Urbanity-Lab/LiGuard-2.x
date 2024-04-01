import open3d.visualization.gui as gui

from config.gui import BaseConfiguration as BaseConfigurationGUI

from pcd.file_io import FileIO as PCD_File_IO
from pcd.sensor_io import SensorIO as PCD_Sensor_IO
from pcd.viz import PointCloudVisualizer

from img.file_io import FileIO as IMG_File_IO
from img.sensor_io import SensorIO as IMG_Sensor_IO
from img.viz import ImageVisualizer

from calib.file_io import FileIO as CLB_File_IO
from lbl.file_io import FileIO as LBL_File_IO

import keyboard, threading, time

class LiGuard:
    def __init__(self):
        self.app = gui.Application.instance
        self.app.initialize()
        
        self.config = BaseConfigurationGUI(self.app)
        config_call_backs = BaseConfigurationGUI.get_callbacks_dict()
        config_call_backs['apply_config'] = [self.reset, self.start]
        config_call_backs['quit_config'] = [self.quit]
        self.config.update_callbacks(config_call_backs)
        
        self.pcd_io = None
        self.pcd_visualizer = None
        
        self.img_io = None
        self.img_visualizer = None

        self.clb_io = None
        
        self.lbl_io = None
        
        self.lock = threading.Lock()
        self.is_running = False # if the app is running
        self.is_playing = False # if the frames are playing
        self.data_dict = dict()
        self.data_dict['current_frame_index'] = 0
        self.data_dict['previous_frame_index'] = -1
        self.data_dict['maximum_frame_index'] = 0
        
        self.app.run()
        
    def handle_key_event(self, event:keyboard.KeyboardEvent):
        if event.event_type == keyboard.KEY_DOWN:
            with self.lock:
                if event.name == 'right':
                    self.is_playing = False
                    if self.data_dict['current_frame_index'] < self.data_dict['maximum_frame_index']:
                        self.data_dict['current_frame_index'] += 1
                elif event.name == 'left':
                    self.is_playing = False
                    if self.data_dict['current_frame_index'] > 0:
                        self.data_dict['current_frame_index'] -= 1
                elif event.name == 'space':
                    self.is_playing = not self.is_playing
        
    def reset(self, cfg):
        keyboard.unhook_all()
        with self.lock: self.is_running = False

        self.data_dict['previous_frame_index'] = -1
        
        if self.pcd_io != None: self.pcd_io.close()
        if cfg['data']['lidar']['enabled']: self.pcd_io = PCD_File_IO(cfg)
        elif cfg['sensors']['lidar']['enabled']: self.pcd_io = PCD_Sensor_IO(cfg)
        else: self.pcd_io = None
        self.data_dict['total_pcd_frames'] = len(self.pcd_io) if self.pcd_io else 0
        
        if self.pcd_io and cfg['visualization']['enabled']:
            if self.pcd_visualizer != None: self.pcd_visualizer.reset(cfg)
            else: self.pcd_visualizer = PointCloudVisualizer(self.app, cfg)
        
        if self.img_io != None: self.img_io.close()
        if cfg['data']['camera']['enabled']: self.img_io = IMG_File_IO(cfg)
        elif cfg['sensors']['camera']['enabled']: self.img_io = IMG_Sensor_IO(cfg)
        else: self.img_io = None
        self.data_dict['total_img_frames'] = len(self.img_io) if self.img_io else 0
        
        if self.img_io and cfg['visualization']['enabled']:
            if self.img_visualizer != None: self.img_visualizer.reset(cfg)
            else: self.img_visualizer = ImageVisualizer(self.app, cfg)

        if self.clb_io != None: self.clb_io.close()
        if cfg['data']['calib']['enabled']: self.clb_io = CLB_File_IO(cfg)
        else: self.clb_io = None
        self.data_dict['total_clb_frames'] = len(self.clb_io) if self.clb_io else 0
        
        if self.lbl_io != None: self.lbl_io.close()
        if cfg['data']['label']['enabled']: self.lbl_io = LBL_File_IO(cfg, self.clb_io.__getitem__ if self.clb_io else None)
        else: self.lbl_io = None
        self.data_dict['total_lbl_frames'] = len(self.lbl_io) if self.lbl_io else 0
        
        self.data_dict['maximum_frame_index'] = max(self.data_dict['total_pcd_frames'], self.data_dict['total_img_frames'], self.data_dict['total_lbl_frames']) - 1
        
        self.lidar_processes = dict()
        for proc in cfg['proc']['lidar']:
            enabled = cfg['proc']['lidar'][proc]['enabled']
            if enabled:
                priority = cfg['proc']['lidar'][proc]['priority']
                process = __import__('algo.lidar', fromlist=[proc]).__dict__[proc]
                self.lidar_processes[priority] = process
        self.lidar_processes = [self.lidar_processes[priority] for priority in sorted(self.lidar_processes.keys())]
        
        self.camera_processes = dict()
        for proc in cfg['proc']['camera']:
            enabled = cfg['proc']['camera'][proc]['enabled']
            if enabled:
                priority = cfg['proc']['camera'][proc]['priority']
                process = __import__('algo.camera', fromlist=[proc]).__dict__[proc]
                self.camera_processes[priority] = process
        self.camera_processes = [self.camera_processes[priority] for priority in sorted(self.camera_processes.keys())]

        self.calib_processes = dict()
        for proc in cfg['proc']['calib']:
            enabled = cfg['proc']['calib'][proc]['enabled']
            if enabled:
                priority = cfg['proc']['calib'][proc]['priority']
                process = __import__('algo.calib', fromlist=[proc]).__dict__[proc]
                self.calib_processes[priority] = process
        self.calib_processes = [self.calib_processes[priority] for priority in sorted(self.calib_processes.keys())]
        
        self.label_processes = dict()
        for proc in cfg['proc']['label']:
            enabled = cfg['proc']['label'][proc]['enabled']
            if enabled:
                priority = cfg['proc']['label'][proc]['priority']
                process = __import__('algo.label', fromlist=[proc]).__dict__[proc]
                self.label_processes[priority] = process
        self.label_processes = [self.label_processes[priority] for priority in sorted(self.label_processes.keys())]
        
        self.post_processes = dict()
        for proc in cfg['proc']['post']:
            enabled = cfg['proc']['post'][proc]['enabled']
            if enabled:
                priority = cfg['proc']['post'][proc]['priority']
                process = __import__('algo.post', fromlist=[proc]).__dict__[proc]
                self.post_processes[priority] = process
        self.post_processes = [self.post_processes[priority] for priority in sorted(self.post_processes.keys())]
        
    def start(self, cfg):
        with self.lock: self.is_running = True
        
        if self.pcd_visualizer or self.img_visualizer: keyboard.hook(self.handle_key_event)
        
        while True:
            with self.lock:
                if not self.is_running: break
                elif self.is_playing and self.data_dict['current_frame_index'] < self.data_dict['maximum_frame_index']: self.data_dict['current_frame_index'] += 1
            
            frame_changed = self.data_dict['previous_frame_index'] != self.data_dict['current_frame_index']
            
            if frame_changed:
                self.data_dict['previous_frame_index'] = self.data_dict['current_frame_index']
                
                if self.pcd_io:
                    current_point_cloud_path, current_point_cloud_numpy = self.pcd_io[self.data_dict['current_frame_index']]
                    self.data_dict['current_point_cloud_path'] = current_point_cloud_path
                    self.data_dict['current_point_cloud_numpy'] = current_point_cloud_numpy
                elif 'current_point_cloud_numpy' in self.data_dict: self.data_dict.pop('current_point_cloud_numpy')
                
                if self.img_io:
                    current_image_path, current_image_numpy = self.img_io[self.data_dict['current_frame_index']]
                    self.data_dict['current_image_path'] = current_image_path
                    self.data_dict['current_image_numpy'] = current_image_numpy
                elif 'current_image_numpy' in self.data_dict: self.data_dict.pop('current_image_numpy')

                if self.clb_io:
                    current_calib_path, current_calib_data = self.clb_io[self.data_dict['current_frame_index']]
                    self.data_dict['current_calib_path'] = current_calib_path
                    self.data_dict['current_calib_data'] = current_calib_data
                elif 'current_calib_data' in self.data_dict: self.data_dict.pop('current_calib_data')
                
                if self.lbl_io:
                    current_label_path, current_label_list = self.lbl_io[self.data_dict['current_frame_index']]
                    self.data_dict['current_label_path'] = current_label_path
                    self.data_dict['current_label_list'] = current_label_list
                elif 'current_label_list' in self.data_dict: self.data_dict.pop('current_label_list')
            
                if self.pcd_io:
                    for proc in self.lidar_processes: proc(self.data_dict, cfg)
                if self.img_io:
                    for proc in self.camera_processes: proc(self.data_dict, cfg)
                if self.clb_io:
                    for proc in self.calib_processes: proc(self.data_dict, cfg)
                if self.lbl_io:
                    for proc in self.label_processes: proc(self.data_dict, cfg)
                
                for proc in self.post_processes: proc(self.data_dict, cfg)
            
                if self.pcd_io:
                    self.pcd_visualizer.update(self.data_dict)
                    self.pcd_visualizer.redraw()
                if self.img_io:
                    self.img_visualizer.update(self.data_dict)
                    self.img_visualizer.redraw()
                    
            else:
                if self.pcd_io: self.pcd_visualizer.redraw()
                if self.img_io: self.img_visualizer.redraw()
            
            time.sleep(cfg['threads']['vis_sleep'])
            
    def quit(self, cfg):
        with self.lock: self.is_running = False
        keyboard.unhook_all()
        
        if self.pcd_io: self.pcd_io.close()
        if self.img_io: self.img_io.close()
        if self.lbl_io: self.lbl_io.close()
        
        if self.pcd_visualizer: self.pcd_visualizer.quit()
        if self.img_visualizer: self.img_visualizer.quit()
        
        self.app.quit()
        
def main():
    LiGuard()
    
main()