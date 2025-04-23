import tifffile
import scipy
import numpy as np
from skimage.feature import register_translation
import h5py
import matplotlib.pyplot as plt
from skimage.metrics import structural_similarity
from mindscope_qc_metrics.utils.util import get_psql_dict_cursor
import os
import scipy.ndimage

def get_experiments(experiment_id):
    query = """
    SELECT  
    OE.storage_directory,
    OE.id AS experiment_id,
    OS.date_of_acquisition,
    OS.id AS session_id,
    OS.parent_session_id

    FROM ophys_experiments OE
    
    JOIN ophys_sessions OS ON OS.id = oe.ophys_session_id
    
    WHERE OE.id = {0}
    """
    lims_cursor = get_psql_dict_cursor()
    lims_cursor.execute(query.format(experiment_id))
    records = lims_cursor.fetchall()
    return(records)

def get_sessions(session_id):
    query = """
    SELECT  
    OE.storage_directory,
    OE.id AS experiment_id,
    OS.date_of_acquisition,
    OS.id AS session_id,
    OS.parent_session_id

    FROM ophys_experiments OE
    
    JOIN ophys_sessions OS ON OS.id = oe.ophys_session_id
    
    WHERE OS.id = {0}
    """
    lims_cursor = get_psql_dict_cursor()
    lims_cursor.execute(query.format(session_id))
    records = lims_cursor.fetchall()
    return(records)

def depth_calculator(experiment_id):
    exp_dict = get_experiments(experiment_id)
    current_exp_path = os.path.join('/'+exp_dict[0]['storage_directory'], 'processed/'+str(experiment_id)+'_suite2p_motion_output.h5')

    sorted_session = np.sort([experiment['experiment_id'] for experiment in get_sessions(exp_dict[0]['session_id'])])

    sorted_parent = np.sort([experiment['experiment_id'] for experiment in get_sessions(exp_dict[0]['parent_session_id'])])

    parent_exp_id = sorted_parent[list(sorted_session).index(experiment_id)]

    parent_exp_dict = get_experiments(parent_exp_id)
    parent_exp_path = os.path.join('/'+parent_exp_dict[0]['storage_directory'], 'processed/'+str(parent_exp_id)+'_suite2p_motion_output.h5')

    start_index = 0
    end_index = 500
    with h5py.File(parent_exp_path, 'r') as fin:
        data_parent = fin['data'][start_index:end_index]
    data_parent = np.mean(data_parent, axis = 0)
    print('Parent')
    plt.imshow(data_parent, cmap = 'gray', vmax = np.percentile(data_parent, 99))
    plt.show()
    data_parent_gauss = scipy.ndimage.gaussian_filter(data_parent, sigma=5)

    start_index = 0
    end_index = 500
    with h5py.File(current_exp_path, 'r') as fin:
        data_current = fin['data'][start_index:end_index]
    data_current = np.mean(data_current, axis = 0)
    print('Current')
    plt.imshow(data_current, cmap = 'gray', vmax = np.percentile(data_current, 99))
    plt.show()
    data_current_gauss = scipy.ndimage.gaussian_filter(data_current, sigma=5)

    local_stack_dir = r'\\allen\programs\mindscope\workgroups\learning\mouse-qc\qc' 
    local_stack_filename = '\local_z_stack\local_z_stack.tif' 
    stack = tifffile.imread(os.path.join(local_stack_dir, str(parent_exp_id)+local_stack_filename))
    stack_gauss = scipy.ndimage.gaussian_filter(stack, (0, 5, 5))

    stack_mean = np.max(stack, axis = 0)

    shift_parent, _, _ = register_translation(
        data_parent, stack_mean)
    shift_current, _, _ = register_translation(
        data_current, stack_mean)

    coeffs_parent = [structural_similarity(data_parent_gauss, scipy.ndimage.shift(zplane, shift_parent).astype(np.float64)) for zplane in stack_gauss]
    coeffs_current = [structural_similarity(data_current_gauss, scipy.ndimage.shift(zplane, shift_current).astype(np.float64)) for zplane in stack_gauss]
    print(str((int(np.argmax(coeffs_parent))-int(np.argmax(coeffs_current)))*0.75)+'um calculated depth difference')

    plt.plot(coeffs_parent, label = 'Parent Match')
    plt.plot(coeffs_current, label = 'Current Match')
    plt.axvline(int(np.argmax(coeffs_parent)), c= 'k')
    plt.axvline(int(np.argmax(coeffs_current)), c = 'k')
    plt.title('Parent and Current Depth Matched\non Parent Local Z Stack')
    plt.xlabel('Frame #')
    plt.ylabel('SSIM Score')
    plt.legend()
    plt.show()