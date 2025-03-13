import numpy as np
import matplotlib.pyplot as plt
import h5py
from skimage.external import tifffile as tif
from scipy import ndimage
from mindscope_qc_metrics.utils.util import get_psql_dict_cursor
import matplotlib.patches as patches
import os
def get_job_status(session_id):
    """
    session_id (int): LIMS ophys session ID 
    Pulls the basic records information for a LIMS ophys session.  Returns dictionary of relevant info
    *Will need to edit this for code-ocean eventually*
    """
    query = """
    SELECT  
    OS.storage_directory,
    OS.id AS Session_ID,
    isi.storage_directory as isi_directory
    
    FROM ophys_sessions OS
    JOIN isi_experiments isi ON isi.id = os.isi_experiment_id

    WHERE os.id = {0}
    """
    lims_cursor = get_psql_dict_cursor()
    lims_cursor.execute(query.format(session_id))
    records = lims_cursor.fetchall()
    return(records)

def fullfield_roi_drawer(data):
    """
    Input the fullfield h5 file and returns the coords for box
    """
    import json
    fullfield_meta = json.loads(data['full_field_metadata'][()].decode('utf-8'))
    coords_list = []
    coords2 = []
    for roi in fullfield_meta[1]['RoiGroups']['imagingRoiGroup']['rois']:
        coords_list.append(roi['scanfields']['centerXY'])
        coords2.append(roi['scanfields']['sizeXY'])
    x, y = zip(*coords_list)
    left = [coord+(coords2[0][0]/2) for coord in x]
    right = [coord-(coords2[0][0]/2) for coord in x]
    top= [coord+(coords2[0][1]/2) for coord in y]
    bot = [coord-(coords2[0][1]/2) for coord in y]
    return(x,y[0], left, right, top[0], bot[0])

def surface_roi_drawer(data):
    """
    Input the fullfield h5 file and returns the coords for box
    """
    import json
    surface_meta = json.loads(data['surface_roi_metadata'][()].decode('utf-8'))
    coords_list = []
    coords2 = []
    for roi in surface_meta[1]['RoiGroups']['imagingRoiGroup']['rois']:
        if roi=='ver':
            roix, roiy =surface_meta[1]['RoiGroups']['imagingRoiGroup']['rois']['scanfields']['centerXY']
            coords_list.append([roix, roiy])
            roiw, roih = surface_meta[1]['RoiGroups']['imagingRoiGroup']['rois']['scanfields']['sizeXY']
            coords2.append([roiw, roih])
            break
        else:
            roix, roiy = roi['scanfields']['centerXY']
            roiw, roih = roi['scanfields']['sizeXY']
            coords_list.append([roix, roiy])
            coords2.append([roiw, roih])
    x, y = zip(*coords_list)
    w, h = zip(*coords2)
    return(list(x),list(y), list(w), list(h))

def fullfield_match_maker(session_id, isi_rotation = 290):
    """Takes a LIMS ophys session and pulls scanimage metadata information from the surface metadata and the 
    fullfield metadata in order to draw ROIs on the fullfield mapped tif file  making it easier to read.  
    Also pulls the ISI map and rotates it to allow for side by side comparison

    Args:
        session_id (int): LIMS ophys session ID
        isi_rotation (int, optional): degrees to rotate the ISI map.  May vary depending on the surgery on the mouse. Defaults to 290.
    """
    #load the data
    if session_id == False:
        print('session_id variable empty. save variable again')
    try:
        image = '/'+os.path.join(get_job_status(session_id)[0]['storage_directory'], str(session_id)+"_stitched_full_field_img.h5")
        data = h5py.File(image)
        task1 = True
    except:
        print('stitched fullfield not found')
        task1 = False

    try:
        isi = get_job_status(session_id)[0]['isi_directory']
        isi_experiment = isi.split('/')[-2]
        isi_experiment = isi_experiment.split('_')[-1]
        isi_path = '/'+os.path.join(isi, str(isi_experiment)+"_target_map.tif")
        isi_tif = tif.imread(isi_path)
        task2 = True
    except:
        print('no isi image found')
        task2 = False
    #tweak this rotation if your Fullfield image does not line up properly
    rotation = isi_rotation

    if task1 and task2 ==True:
        #print the images
        array = data['stitched_full_field_with_rois']
        rotated_img = ndimage.rotate(isi_tif, rotation)

        x, y, left, right, top, bot = fullfield_roi_drawer(data)
        fig, (ax1, ax3) = plt.subplots(1,2,figsize=(16,7))
        plt.suptitle('Fullfield ROI match VS ISI')
        ax1.set_axis_off()

        ax3.set_axis_off()
        ax1.set_title('Fullfield w/ROIs')
        ax3.set_title('Vasculature w/ISI')
        ax1.imshow(data['stitched_full_field_with_rois'], aspect = 'auto', cmap=plt.cm.gray, vmin = 0, vmax = np.percentile(data['stitched_full_field_with_rois'], 98))
        ax1.set_xlim(0, np.shape(data['stitched_full_field_with_rois'][()])[1])
        ax1.set_ylim(0, np.shape(data['stitched_full_field_with_rois'][()])[0])
        ax2 = ax1.twinx().twiny()
        ax2.set_axis_off()
        roix_list, roiy_list, roiw_list, roih_list = surface_roi_drawer(data)
        for n in range(len(roix_list)):
            roix= roix_list[n]
            roiy= roiy_list[n]
            roiw= roiw_list[n]
            roih= roih_list[n]        
            ax2.add_patch(patches.Rectangle([roix-roiw/2, (roiy-roih/2)], roiw, roih, fill = False, color = 'red', linewidth = 3))
        ax2.set_xlim(np.min(right), np.max(left))
        ax2.set_ylim(bot,top)
        #ax2.invert_yaxis()
        ax3.imshow(rotated_img)

        #plt.tight_layout()
        #ax1.invert_yaxis()

        plt.savefig(r"\\10.128.49.67\meso_dev_data\operator_files\fullfieldROImatch_output"+'\\'+str(session_id)+'_fullfieldROImatch.png')
        plt.show()
        task1 == False
        task2 == False
        session_id = False


