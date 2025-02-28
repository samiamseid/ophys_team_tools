from mindscope_qc_metrics.utils.util import get_psql_dict_cursor
import pandas as pd

def fetch_sessions_in_project(project):
    """returns dictionary of sessions associated with a project code

    Args:
        project (str): LIMS project code to query
    """
    all_query = '''
    select os.id, p.code, os.date_of_acquisition, os.workflow_state, s.external_specimen_name as mouse_id, s.name as cre_line, os.stimulus_name
    FROM ophys_sessions os
    JOIN projects p ON os.project_id = p.id
    JOIN specimens s ON os.specimen_id = s.id
    WHERE p.code IN ({0})
    '''
    lims_cursor = get_psql_dict_cursor()
    lims_cursor.execute(all_query.format(project))
    records = lims_cursor.fetchall()
    return(records)

def dict_to_dataframe(dict):
    """Converts dictionary output to pandas dataframe 

    Args:
        dict (dictionary): dictionary output of LIMS query
    """

    return(pd.DataFrame(dict))

def sessions_per_mouse(dataframe):
    """input dataframe and output how many sessions collected for each unique mouse ID

    Args:
        dataframe (pandas dataframe): pandas dataframe of LIMS query
    """

    return(df_up.mouse_id.value_counts())

