import tifffile
import scipy
import numpy as np
from skimage.feature import register_translation
import h5py
import matplotlib.pyplot as plt
from mindscope_qc_metrics.utils.util import get_psql_dict_cursor
import os
from skimage.metrics import structural_similarity as ssim
import pandas as pd

def crop_image(image, shift_xy):
    _shape = image.shape
    crop = (int(np.abs(np.floor(shift_xy[0]))), int(np.abs(np.floor(shift_xy[1]))))
    px_y_start, px_x_start = crop
    px_y_end = _shape[0] - px_y_start
    px_x_end = _shape[1] - px_x_start
    image = image[px_y_start:px_y_end, px_x_start:px_x_end]
    return(image)

def crop_stack(z_stack, shift_xy):
    _shape = z_stack.shape
    crop = (int(np.abs(np.floor(shift_xy[0]))), int(np.abs(np.floor(shift_xy[1]))))
    px_y_start, px_x_start = crop
    px_y_end = _shape[1] - px_y_start
    px_x_end = _shape[2] - px_x_start
    z_stack = z_stack[:, px_y_start:px_y_end, px_x_start:px_x_end]
    return(z_stack)

def output_shift(image1, image2):
    shift, _, _ = register_translation(
    image1, image2)
    return(shift)

def shift_stack(stack, shift):
    shift = np.insert(shift, 0, 0, axis=0)
    shifted_img = scipy.ndimage.shift(stack, shift)
    return(shifted_img)

def physio_mean(filepath, start_index = 0, end_index = 500):
    start_index = start_index
    end_index = end_index
    with h5py.File(filepath, 'r') as fin:
        data = fin['data'][start_index:end_index]
    data = np.mean(data, axis = 0)
    return(data)
        
def calculate_ssim(image, zstack):
    coeffs = [ssim(image.astype('uint16'), zplane) for zplane in zstack]
    return(coeffs)

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

def stack_load(filepath):
    stack = tifffile.imread(filepath)
    return(stack)

def stack_gauss(stack):
    stack_gauss = scipy.ndimage.gaussian_filter(stack, (0, 5, 5))
    return(stack_gauss)

def image_gauss(image):
    image_gauss = scipy.ndimage.gaussian_filter(image, (5, 5))
    return(image_gauss)

def get_stack_mean(stack):
    stack_mean = np.max(stack, axis = 0)
    return(stack_mean)

def get_paths(experiment_id):
    exp_dict = get_experiments(experiment_id)
    current_exp_path = os.path.join('/'+exp_dict[0]['storage_directory'], 'processed/'+str(experiment_id)+'_suite2p_motion_output.h5')
    sorted_session = np.sort([experiment['experiment_id'] for experiment in get_sessions(exp_dict[0]['session_id'])])
    sorted_parent = np.sort([experiment['experiment_id'] for experiment in get_sessions(exp_dict[0]['parent_session_id'])])
    parent_exp_id = sorted_parent[list(sorted_session).index(experiment_id)]
    parent_exp_dict = get_experiments(parent_exp_id)
    parent_exp_path = os.path.join('/'+parent_exp_dict[0]['storage_directory'], 'processed/'+str(parent_exp_id)+'_suite2p_motion_output.h5')
    local_stack_dir = r'\\allen\programs\mindscope\workgroups\learning\mouse-qc\qc' 
    local_stack_filename = '\local_z_stack\local_z_stack.tif' 
    stack = os.path.join(local_stack_dir, str(parent_exp_id)+local_stack_filename)
    return(current_exp_path, parent_exp_path, stack)

def prepare_directory(experiment_id):
    storage_path = os.environ['MQCM_IMAGE_STORAGE_DIR']+'\\'+str(experiment_id)+'\\cell_matching'
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
    return(storage_path)

def plot_ssim(coeffs_parent, coeffs_current, experiment_id):
    plt.plot(coeffs_parent, label = 'Parent Match')
    plt.plot(coeffs_current, label = 'Current Match')
    plt.axvline(int(np.argmax(coeffs_parent)), c= 'k')
    plt.axvline(int(np.argmax(coeffs_current)), c = 'k')
    plt.title('Parent and Current Depth Matched\non Parent Local Z Stack')
    plt.xlabel('Frame #')
    plt.ylabel('SSIM Score')
    plt.legend()
    filename = 'ssim_score_plot.png'
    plt.savefig(os.path.join(prepare_directory(experiment_id), filename))

def plot_images(parent, child, experiment_id):
    plt.figure()
    f, ax = plt.subplots(1,2)
    ax[0].imshow(parent)
    ax[0].set_title('Parent Physio Start')
    ax[1].imshow(child)
    ax[1].set_title('Current Physio Start')
    filename = 'roi_matching.png'
    plt.savefig(os.path.join(prepare_directory(experiment_id), filename))

def save_metrics(metrics_dict, experiment_id):
    pd.DataFrame([metrics_dict]).to_csv(os.path.join(os.getenv('MQCM_IMAGE_STORAGE_DIR')+'\\'+str(experiment_id)+'\\cell_matching', str(experiment_id)+'_cellmatch_metrics.csv'))
    
def depth_calculator(experiment_id):
    #load the data
    child, parent, stack = get_paths(experiment_id)
    child = physio_mean(child)
    parent = physio_mean(parent)
    stack = stack_load(stack)
    
    #register stack to child plane
    stack_mean = get_stack_mean(stack)
    shift_child = output_shift(child,stack_mean)
    child_cropped = crop_image(child, shift_child)
    stack_child = crop_stack(shift_stack(stack, shift_child), shift_child)
    
    #calculate child SSIM
    coeffs_current = calculate_ssim(image_gauss(child_cropped), stack_gauss(stack_child))
    
    #register stack to parent plane
    shift_parent = output_shift(parent, stack_mean)
    parent_cropped = crop_image(parent, shift_parent)
    stack_parent = crop_stack(shift_stack(stack, shift_parent), shift_parent)
    
    #calculate parent SSIM
    coeffs_parent = calculate_ssim(image_gauss(parent_cropped), stack_gauss(stack_parent))
    
    shift_matching = output_shift(parent, child)
    
    plot_images(parent, child, experiment_id)
    print(str(shift_matching[1]*0.78125)+'um mismatch in X. '+str(shift_matching[0]*0.78125)+'um mismatch in Y.')
    plot_ssim(coeffs_parent, coeffs_current, experiment_id)
    print(str((int(np.argmax(coeffs_parent))-int(np.argmax(coeffs_current)))*0.75)+'um calculated depth mismatch')
    metrics_dict = {
        'parent_match_frame': int(np.argmax(coeffs_parent)),
        'child_match_frame': int(np.argmax(coeffs_current)),
        'match_drift_frames': int(np.argmax(coeffs_parent))-int(np.argmax(coeffs_current)),
        'match_drift_um': (int(np.argmax(coeffs_parent))-int(np.argmax(coeffs_current)))*0.75,
        'parent_match_ssim_score': coeffs_parent[int(np.argmax(coeffs_parent))],
        'child_match_ssim_score': coeffs_current[int(np.argmax(coeffs_current))],
        'experiment_id': experiment_id
    }
    return(metrics_dict)
