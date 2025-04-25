from ophys_tools import depth_matching_tool as dmt
from datetime import datetime, timedelta
import pandas as pd
import schedule
import time
from mindscope_qc_metrics.utils.util import get_psql_dict_cursor

def get_experiments():
    query = """
    SELECT  
    OE.storage_directory,
    OE.id AS Session_ID,
    OS.date_of_acquisition

    FROM ophys_experiments OE
    
    JOIN ophys_sessions OS ON OS.id = oe.ophys_session_id
    """
    lims_cursor = get_psql_dict_cursor()
    lims_cursor.execute(query.format())
    records = lims_cursor.fetchall()
    return(records)

def job(t):
    print("I'm working...", t)
    df = pd.DataFrame(get_experiments())
    recent_date = df.sort_values(by = 'date_of_acquisition').dropna().reset_index(drop = True)['date_of_acquisition'].iloc[-1]
    d = recent_date - timedelta(days=1)
    experiment_ids = df[df['date_of_acquisition']>d]['session_id'].values
    for id in experiment_ids:
        try:
            dmt.save_metrics(dmt.depth_calculator(id))

        except:
            print('Issue processing '+str(id))

schedule.every().day.at("01:00").do(job,'It is 01:00am')

while True:
    schedule.run_pending()
    print(str(datetime.today())+ ' :No Job Detected')
    time.sleep(3600)
