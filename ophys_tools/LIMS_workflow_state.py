from mindscope_qc_metrics.utils.util import get_psql_dict_cursor

def get_experiment_job_status():
    """
    pulls a dictionary of all LIMS jobs associated with ophys experiments
    """
    query = """
    SELECT  
    OS.date_of_acquisition,
    OS.id AS Session_ID,
    OS.workflow_state AS Session_workflowstate,
    OE.id AS Experiment_ID,
    OE.workflow_state AS experiment_workflowstate, 
    OE.calculated_depth as depth,
    PR.code,
    SP.external_specimen_name AS Mouse_ID,
    D.full_genotype AS cre_line,
    OE.name AS Experiment_name,
    JOBS.name AS JOB_workflow_state,
    JOBQ.name AS JOB_queue_name,
    JOB.enqueued_at,
    JOB.completed_at

    FROM ophys_sessions OS

    INNER JOIN ophys_experiments OE
    ON OS.id = OE.ophys_session_id
    INNER JOIN projects PR
    ON OS.project_id = PR.id
    INNER JOIN specimens SP
    ON OS.specimen_id = SP.id
    INNER JOIN jobs JOB 
    ON JOB.enqueued_object_id = OE.id
    INNER JOIN job_queues JOBQ
    ON JOBQ.id = JOB.job_queue_id
    INNER JOIN job_states JOBS
    on JOBS.id = JOB.job_state_id
    INNER JOIN donors D
    ON D.id = SP.donor_id

    ORDER BY date_of_acquisition DESC
    """
    lims_cursor = get_psql_dict_cursor()
    lims_cursor.execute(query.format())
    records = lims_cursor.fetchall()
    return(records)

def get_session_job_status():
    """
    pulls a dictionary of all LIMS jobs associated with ophys experiments
    """
    query = """
    SELECT  
    OS.date_of_acquisition,
    OS.id AS Session_ID,
    OS.workflow_state AS Session_workflowstate,
    PR.code,
    SP.external_specimen_name AS Mouse_ID,
    D.full_genotype AS cre_line,
    JOBS.name AS JOB_workflow_state,
    JOBQ.name AS JOB_queue_name,
    JOB.enqueued_at,
    JOB.completed_at

    FROM ophys_sessions OS

    INNER JOIN projects PR
    ON OS.project_id = PR.id
    INNER JOIN specimens SP
    ON OS.specimen_id = SP.id
    INNER JOIN jobs JOB 
    ON JOB.enqueued_object_id = OS.id
    INNER JOIN job_queues JOBQ
    ON JOBQ.id = JOB.job_queue_id
    INNER JOIN job_states JOBS
    on JOBS.id = JOB.job_state_id
    INNER JOIN donors D
    ON D.id = SP.donor_id

    ORDER BY date_of_acquisition DESC
    """
    lims_cursor = get_psql_dict_cursor()
    lims_cursor.execute(query.format())
    records = lims_cursor.fetchall()
    return(records)

def timezone_convert(dataframe, timezone = 'US/Pacific'):
    """Converts the UTC to a more easily understood timezone

    Args:
        dataframe (pandas dataframe): dataframe object in the format of the output for get_job_status function
        timezone (str, optional): timezone to convert into. Defaults to 'US/Pacific'.
    """
    from matplotlib import dates as mdates

    plt.rcParams['timezone'] = timezone
    df = dataframe
    df= df.sort_values(by = 'date_of_acquisition', ascending = False).reset_index(drop = True)
    df['completed_at'] = df['completed_at'].dt.tz_localize('utc').dt.tz_convert(timezone)
    df['enqueued_at'] = df['enqueued_at'].dt.tz_localize('utc').dt.tz_convert(timezone)
    return(df)

def experiment_jobs_to_reprocess(data, mouse_id):
    """input lims query dataframe and relevant mouse_id to return which experiment IDs are still stuck in processing

    Args:
        data (pandas dataframe): _description_
        mouse_id (str): _description_
    """
    df = data[data['mouse_id']==mouse_id]
    df = df[df['experiment_workflowstate']!='created']
    df = df[df['job_queue_name']!='CHANGE_OPHYS_EXPERIMENT_STATE_QC_QUEUE']
    experiments_in_processing = []
    for experiment in df.experiment_id.unique():
        df_exp = df[df['experiment_id']==experiment]
        if 'FAILURE' not in df_exp.job_workflow_state.unique():
            pass
        else:
            for job in df_exp.job_queue_name.unique():
                df_job = df_exp[df_exp['job_queue_name']==job]
                if 'FAILURE' not in df_job.job_workflow_state.unique():
                    pass
                else:
                    df_job = df_job.sort_values(by='enqueued_at')
                    if df_job['job_workflow_state'].values[-1]=='SUCCESS':
                        pass
                    else:
                        experiments_in_processing.append(experiment)

    return(experiments_in_processing)