# the purpose of this package is to extract power in mW from the mesoscope scanimage percent total and percent split values, using our weekly power readings calculations. 

import pandas as pd
import numpy as np

def readings_df(filepath, rig, date = None):
    """
    extract the table from the most recent power readings table.
    filepath = path to power readings recordings
    rig = mesoscope to pull readings from
    # 2/27/2025 Note that readings table is not currently standardized so column names are subject to change -SS
    """
    df = pd.read_csv(filepath)
    df = df[df['rig']==rig]
    df['date_dt'] = pd.to_datetime(df.date)
    if date != None:
        df[df['date_dt']<=date]
    recent = df.sort_values(by = 'date_dt')['date_dt'].unique()[-1]
    df = df[df['date_dt']==recent]

    #beam1 data
    columns_beam1 = [column for column in df.columns if 'beam1' in column]
    df_beam1 = df[columns_beam1]
    df_beam1['total_power'] = df['total_power']
    
    #beam2 data
    df_beam2 = df[df.columns[~df.columns.isin(['rig', 'date', 'total_power', 'date_dt'])]]
    pair = 0
    for i in range(0, len(df_beam2.columns), 2):
        if pair + 1 < len(df_beam2.columns):
            name = str(df_beam2.columns[pair].split('_')[0])+'_beam2_'+str(df_beam2.columns[pair].split('_')[-1])
            df_beam2[name] = df_beam2.iloc[:, pair+1] - df_beam2.iloc[:, pair]
            pair+=2
    columns_beam2 = [column for column in df_beam2.columns if 'beam2' in column]
    df_beam2 = df_beam2[columns_beam2]
    df_beam2['total_power'] = df['total_power']

    return(df_beam1, df_beam2)

def normalize_data(df, variable):
    """Normalize each series of data to 1 so that it can be later converted back to the original data

    Args:
        df (pandas dataframe): beam specific dataframe output of readings_df
        variable (string): total or split, determines which axis to normalize the data
    """
    #normalize relationship of power from 0 to 100% across all split values. 
    if variable =='total':
        columns = [column for column in df.columns if 'beam' in column]
        norm_list = []
        for column in columns:
            df_temp = df[column]
            norm = df_temp/np.max(df_temp)
            norm_list.append(norm)
        df_norm = pd.DataFrame(norm_list)
        df_norm = df_norm.T
        df_norm['total_power']= [0, 20, 40 , 60, 80, 100]
        df_norm['mean'] = np.nanmean(df_norm[columns], axis = 1)
    #normalize relationship for split from 0% to 100% across all total powers by rotating the table and applying same calculations
    elif variable =='split':
        columns = [column for column in df.columns if 'beam' in column]
        dft = df[columns].T
        columns_t = dft.columns
        norm_list = []
        for column in columns_t:
            df_temp = dft[column]
            norm = df_temp/np.max(df_temp)
            norm_list.append(norm)
        df_norm = pd.DataFrame(norm_list)
        df_norm = df_norm.T
        df_norm = df_norm.reset_index(drop = True)
        df_norm.columns = [0, 20, 40, 60, 80, 100]
        df_norm['split'] = [0, 20, 40, 60, 80, 100]
        df_norm['mean'] = np.nanmean(df_norm[[0, 20, 40, 60, 80, 100]], axis = 1)
    else:
        print('variable not recognized.  Please use "total" or "split"')

    return(df_norm)

def fit_data(df_norm, variable, fit = 'linear'):
    """Fits a polynomial equation to the normalized points in the data table

    Args:
        df_norm (dataframe): normalized dataframe output from normalize_data
        variable (str): 'total' or 'split'.  Total will calculate based of the linear relationship, split will use a 3rd order polynomial
        rig (str): 'meso1' or 'meso2'.  Temporary fix for meso1 total power being non-linear (exponential). uses 2 degree polynomial for meso1
    """

    y = df_norm['mean']

    #total power relationship is a linear equation
    if variable =='total':
        if fit =='linear':
            degree = 1
        elif fit =='exponential':
            degree = 2
        else:
            return('Not a valid fit.  Please select "linear" or "exponential"')
        x = df_norm['total_power']
    #split power relationship is a 3rd order polynomial
    elif variable =='split':
        degree = 3
        x = df_norm['split']
    else:
        print('variable not recognized.  Please use "total" or "split"')
    coefficients = np.polyfit(x, y, degree)

    # Create a polynomial function
    poly_func = np.poly1d(coefficients)

    return(poly_func)

def calculate_power(filepath, rig, total_percent, split_percent, date = None):
    """This function calculates the power in each beam for a pair of planes based off the most recent power
      recordings, and the tolta/split for the relevant pair of planes

    Args:
        filepath (str): filepath to the power readings table
        rig (str): name of the rig to pull power readings from (meso1 or meso2)
        total_percent (int): total power percent used in the pair of planes
        split_percent (int): split power percent used in the pair of planes
    """
    from scipy.interpolate import RegularGridInterpolator
    total_levels = np.array([0, 20, 40, 60, 80, 100])
    split_levels = np.array([0, 20, 40, 60, 80, 100])

    #pull relevant dfs
    df_beam1, df_beam2 = readings_df(filepath, rig, date=date)
    df1_drop = df_beam1.drop('total_power', axis =1) 
    df2_drop = df_beam2.drop('total_power', axis =1)

    df1_interp = RegularGridInterpolator((total_levels, split_levels), df1_drop.values)
    df2_interp = RegularGridInterpolator((total_levels, split_levels), df2_drop.values)
    point=np.array([[total_percent, split_percent]])
    beam1_power = df1_interp(point)[0]
    beam2_power = df2_interp(point)[0]

    return(beam1_power, beam2_power)

