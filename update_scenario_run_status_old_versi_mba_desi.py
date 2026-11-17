##step

import dataiku
from dataiku import pandasutils as pdu
import pandas as pd
from datetime import datetime, timezone, timedelta
import pprint

active_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
successful_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
failed_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
not_run_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
aborted_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}

# --- Tambahan: daftar scenario manual di luar pattern RAW_/RFD_/BUS_ ---
extra_scenarios = [
    {'project_key': 'CLEANSING_OID', 'scenario_id': 'IGST_SC_CLEANSING_OID', 'layer': 'T1'},
    {'project_key': 'BUS_CUSTOMER', 'scenario_id': 'BUS_SC_PUB_CUSTOMER360', 'layer': 'T3'},
    {'project_key': 'BUS_RFM_ANALYTIC', 'scenario_id': 'BUS_SC_RFMQT_CURRENT_DAILY', 'layer': 'T3'},
    
    # tambahkan scenario lain di sini kalau ada
]

tz = timezone(timedelta(hours=7))
today = datetime.now(tz).replace(hour=0,minute=0,second=0,microsecond=0)

def scenario_for_layer(layer, id):
    if layer == 'T1':
        return id.startswith('EXEC_SC')
    if layer == 'T2' or layer == 'T3':
        return id.startswith('TRIGGER_EXEC_SC')
    raise Exception('Invalid layer')
    
    
def get_latest_status_today(scenario):
    runs = [r for r in scenario.get_last_runs() if r.start_time >= today]
    sorted(runs, key=lambda r: r.start_time, reverse=True)
    
    if not runs or runs[0].running:
        return 'NOT RUN'
    try:
        return runs[0].outcome
    except:
        return 'ABORTED'

client = dataiku.api_client()
all_project = client.list_project_keys()

def get_layer_code(layer):
    if layer.startswith('RAW_'):
        return 'T1'
    if layer.startswith('RFD_'): 
        return 'T2'
    if layer.startswith('BUS_'): 
        return 'T3' 
    return ''
    
    
for p in all_project:
    if not (p.startswith('RAW_') or p.startswith('RFD_') or p.startswith('BUS_')):
        continue
    layer_code = get_layer_code(p)
    project = client.get_project(p)
    all_scenarios = project.list_scenarios()
    for s in all_scenarios:
        if s['active'] and scenario_for_layer(layer_code, s['id']):
            active_scenarios[layer_code].append(s)
            status = get_latest_status_today(s.to_scenario())
            if status == 'SUCCESS' or status == 'WARNING':
                successful_scenarios[layer_code].append(s)
            elif status == 'NOT RUN':
                not_run_scenarios[layer_code].append(s)
            elif status == 'ABORTED':
                aborted_scenarios[layer_code].append(s)
            else:
                failed_scenarios[layer_code].append(s)

# --- Proses scenario tambahan (manual override) ---
for extra in extra_scenarios:
    project = client.get_project(extra['project_key'])
    layer_code = extra['layer']
    try:
        s_list = project.list_scenarios()
        s = next((x for x in s_list if x['id'] == extra['scenario_id']), None)
        if s is None:
            print(f"$Log: Scenario {extra['scenario_id']} tidak ditemukan di project {extra['project_key']}")
            continue
        if s['active']:
            active_scenarios[layer_code].append(s)
            status = get_latest_status_today(s.to_scenario())
            if status == 'SUCCESS' or status == 'WARNING':
                successful_scenarios[layer_code].append(s)
            elif status == 'NOT RUN':
                not_run_scenarios[layer_code].append(s)
            elif status == 'ABORTED':
                aborted_scenarios[layer_code].append(s)
            else:
                failed_scenarios[layer_code].append(s)
    except Exception as e:
        print(f"$Log: Error processing extra scenario {extra['scenario_id']}: {e}")

print(f'$Log: Writing report')
monitoring_report = []

# Failed scenarios
for layer in failed_scenarios:
    for s in failed_scenarios[layer]:
        row = {
            'PROJECT_NAME': s['projectKey'],
            'SCENARIO_NAME': s['id'],
            'LAYER': layer,
            'STATUS': 'FAILED'
        }
        monitoring_report.append(row)

# Not run scenarios        
for layer in not_run_scenarios:
    for s in not_run_scenarios[layer]:
        row = {
            'PROJECT_NAME': s['projectKey'],
            'SCENARIO_NAME': s['id'],
            'LAYER': layer,
            'STATUS': 'NOT RUN'
        }
        monitoring_report.append(row)

# Aborted scenarios
for layer in aborted_scenarios:
    for s in aborted_scenarios[layer]:
        row = {
            'PROJECT_NAME': s['projectKey'],
            'SCENARIO_NAME': s['id'],
            'LAYER': layer,
            'STATUS': 'ABORTED'
        }
        monitoring_report.append(row)
        
df = pd.DataFrame.from_dict(monitoring_report)
ds = dataiku.Dataset('SCENARIO_REPORT')
ds.write_with_schema(df)



##metrics

import dataiku
from datetime import datetime, timezone, timedelta

active_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
successful_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
failed_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
not_run_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}
aborted_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}

# --- Tambahan: daftar scenario manual di luar pattern RAW_/RFD_/BUS_ ---
extra_scenarios = [
    {'project_key': 'CLEANSING_OID', 'scenario_id': 'IGST_SC_CLEANSING_OID', 'layer': 'T1'},
    {'project_key': 'BUS_CUSTOMER', 'scenario_id': 'BUS_SC_PUB_CUSTOMER360', 'layer': 'T3'},
    {'project_key': 'BUS_RFM_ANALYTIC', 'scenario_id': 'BUS_SC_RFMQT_CURRENT_DAILY', 'layer': 'T3'}
    # tambahkan scenario lain di sini kalau ada
]


tz = timezone(timedelta(hours=7))
today = datetime.now(tz).replace(hour=0,minute=0,second=0,microsecond=0)

def scenario_for_layer(layer, id):
    if layer == 'T1':
        return id.startswith('EXEC_SC')
    if layer == 'T2' or layer == 'T3':
        return id.startswith('TRIGGER_EXEC_SC')
    raise Exception('Invalid layer')
    
    
def get_latest_status_today(scenario):
    runs = [r for r in scenario.get_last_runs() if r.start_time >= today]
    sorted(runs,key=lambda r: r.start_time,reverse=True)
    # print(runs[0].running if runs else 'NOT RUN')
    if not runs or runs[0].running:
        return 'NOT RUN'
    try:
        return runs[0].outcome
    except:
        return 'ABORTED'

client = dataiku.api_client()
all_project = client.list_project_keys()


def get_layer_code(layer):
    if layer.startswith('RAW_'):
        return 'T1'
    if layer.startswith('RFD_'): 
        return 'T2'
    if layer.startswith('BUS_'): 
        return 'T3' 
    return ''
    

# Define here a function that returns the metric.
def process(dataset, partition_id):
    client = dataiku.api_client()
    all_project = client.list_project_keys()
    
    for p in all_project:
        if not (p.startswith('RAW_') or p.startswith('RFD_') or p.startswith('BUS_')):
            continue
        layer_code = get_layer_code(p)
        project = client.get_project(p)
        all_scenarios = project.list_scenarios()
        for s in all_scenarios:
            if s['active'] and scenario_for_layer(layer_code, s['id']):
                active_scenarios[layer_code].append(s)
                status = get_latest_status_today(s.to_scenario())
                if status == 'SUCCESS' or status == 'WARNING':
                    successful_scenarios[layer_code].append(s)
                elif status == 'NOT RUN':
                    not_run_scenarios[layer_code].append(s)
                elif status == 'ABORTED':
                    aborted_scenarios[layer_code].append(s) 
                else:
                    failed_scenarios[layer_code].append(s)
                 
    # --- Proses scenario tambahan (manual override) ---
    for extra in extra_scenarios:
        project = client.get_project(extra['project_key'])
        layer_code = extra['layer']
        try:
            s_list = project.list_scenarios()
            s = next((x for x in s_list if x['id'] == extra['scenario_id']), None)
            if s is None:
                print(f"$Log: Scenario {extra['scenario_id']} tidak ditemukan di project {extra['project_key']}")
                continue
            if s['active']:
                active_scenarios[layer_code].append(s)
                status = get_latest_status_today(s.to_scenario())
                if status == 'SUCCESS' or status == 'WARNING':
                    successful_scenarios[layer_code].append(s)
                elif status == 'NOT RUN':
                    not_run_scenarios[layer_code].append(s)
                elif status == 'ABORTED':
                    aborted_scenarios[layer_code].append(s)
                else:
                    failed_scenarios[layer_code].append(s)
        except Exception as e:
            print(f"$Log: Error processing extra scenario {extra['scenario_id']}: {e}")

        print(f'$Log: Writing report')
        monitoring_report = []
                    
       # dataset is a dataiku.Dataset object
    return {
        'active_t1': len(active_scenarios['T1']),
        'active_t2': len(active_scenarios['T2']),
        'active_t3': len(active_scenarios['T3']),
        'success_t1': len(successful_scenarios['T1']),
        'success_t2': len(successful_scenarios['T2']),
        'success_t3': len(successful_scenarios['T3']),
        'failed_t1': len(failed_scenarios['T1']),
        'failed_t2': len(failed_scenarios['T2']),
        'failed_t3': len(failed_scenarios['T3']),
        'not_run_t1': len(not_run_scenarios['T1']),
        'not_run_t2': len(not_run_scenarios['T2']),
        'not_run_t3': len(not_run_scenarios['T3']),
        'aborted_t1': len(aborted_scenarios['T1']),
        'aborted_t2': len(aborted_scenarios['T2']),
        'aborted_t3': len(aborted_scenarios['T3'])
    }



    
    



