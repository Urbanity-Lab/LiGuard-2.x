"""
algo Package
============
The algo package contains implementations of commonly used components of data processing algorithms to aid researchers utilize these components in their pipelines. The package is divided into sub-modules based on the type of data being processed, such as lidar, camera, calibration, and labels.

Sub-Modules and Their Purposes
------------------------------
- **algo.pre**: Contains generic pre-processing algorithms for data, such as augmentation and normalization.
- **algo.lidar**: Contains algorithms for point cloud processing.
- **algo.camera**: Contains algorithms for image processing.
- **algo.calib**: Contains algorithms for manipulating calibration parameters, like rectification.
- **algo.label**: Contains algorithms for manipulating both read and predicted labels, including filtering based on criteria.
- **algo.post**: Contains generic post-processing algorithms, like saving data in specific formats or directories.

Execution Order
---------------
The order of execution for algorithms within each sub-module is determined by the `priority` parameter in the `base_config.yml` file. Lower priority values correspond to earlier execution. This parameter can be modified in the GUI configuration window. The execution order across sub-modules follows this sequence: `pre` -> `lidar` -> `camera` -> `calib` -> `label` -> `post`.

Contributing a New Algorithm
-----------------------------
If you think that a new algorithm/function can be beneficial for a vast majority of users, you can follow the contribution guidelines and add your algorithm to the appropriate sub-module as described below.

1. Add a YAML configuration entry in the `resources->config_template.yml` under `proc-><sub_module_type>-><your_algo_name>`.
2. Implement the algorithm function in the `<sub_module_type>.py` file within the `algo` package.

For example to add a new lidar algorithm named `dummy`, you would follow these steps:

1. Add the following entry to the `resources->config_template.yml` file:

.. code-block:: yaml

    # configuration for a function in LiGuard is defined in yaml format
    dummy: # name of the function
        enabled: False # bool -- adds the function to pipeline if True -- necessary parameter, don't remove
        priority: 3 # int -- priority of process, lower is higher -- necessary parameter, don't remove
        # parameters are defined as key-value pairs: param_name: param_value
        # `param_name` should always be a string and `param_value` can be any of these types: int, float, bool, str, list, dict
        # examples:
        # threshold: 0.5
        # do_average: true
        # active_classes: ["class_1", "class_2"]
        # score_weights: # a dictionary in yaml format
        #   class_1: 0.4
        #   class_2: 0.6
        # ...

2. Implement the algorithm function in the `lidar.py` file within the `algo` package:

.. code-block:: python

    @algo_func(required_data=[]) # add required keys in the list -- necessary decorator, don't remove
    # following keys are standard to `LiGuard`:
    # `current_point_cloud_path`, `current_point_cloud_numpy`, `current_image_path`, `current_image_numpy`, `current_calib_path`, `current_calib_data`, `current_label_path`, `current_label_list`
    # one or more of the `LiGuard` standard keys can be added to `keys_required_in_data_dict` decorator, for example:
    # @keys_required_in_data_dict(['current_point_cloud_numpy', 'current_image_numpy'])
    # @keys_required_in_data_dict(['current_calib_data'])
    # custom keys can also be added to `keys_required_in_data_dict` decorator if those are generated by any previous algorithm(s) in the pipeline, for example:
    # @keys_required_in_data_dict(['custom_key_1', 'custom_key_2'])
    def FUNCTION_NAME(data_dict: dict, cfg_dict: dict, logger: Logger):
        '''
        A function to perform the algorithmic operations on the data.

        Args:
            data_dict (dict): A dictionary containing the data.
            cfg_dict (dict): A dictionary containing the configuration parameters.
            logger (gui.logger_gui.Logger): A logger object for logging messages and errors in GUI.
        '''
        #########################################################################################################################
        # standard code snippet that gets the parameters from the config file and checks if required data is present in data_dict
        # usually, this snippet is common for all the algorithms, so it is recommended to not remove it
        algo_name = inspect.stack()[0].function
        params = get_algo_params(cfg_dict, algo_type, algo_name, logger)
        
        # check if required data is present in data_dict
        for key in FUNCTION_NAME.required_data:
            if key not in data_dict:
                logger.log(f'{key} not found in data_dict', Logger.ERROR)
                return
        # standard code snippet ends here
        #########################################################################################################################
        # imports
        # import numpy as np
        # ...
        
        # your code
        # def add(a, b): return a + b
        # result = add(params['a'], params['b'])

        # add results to data_dict
        # data_dict[f'{algo_name}_result'] = result
"""