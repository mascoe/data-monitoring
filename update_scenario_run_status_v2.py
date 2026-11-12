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


extra_scenarios = [
    {'project_key': 'CLEANSING_OID', 'scenario_id': 'IGST_SC_CLEANSING_OID', 'layer': 'T1'},
    # {'project_key': 'BUS_CUSTOMER', 'scenario_id': 'BUS_SC_PUB_CUSTOMER360', 'layer': 'T3'}, --list ini tidak diperlukan lagi
    # tambahkan scenario lain di sini kalau ada
]


running_scenarios = {
    'T1': [],
    'T2': [],
    'T3': []
}

tz = timezone(timedelta(hours=7))
today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)


'''
--kita tak perlu filter ini
def scenario_for_layer(layer, id):
    if layer == 'T1':
        return id.startswith('EXEC_SC')
    if layer == 'T2' or layer == 'T3':
        return id.startswith('TRIGGER_EXEC_SC')
    raise Exception('Invalid layer')
'''


def get_latest_status_today(scenario):
    runs = [
        r for r in scenario.get_last_runs()
        if r.start_time >= today
    ]

    # --- FIX: Simpan hasil sorting agar run terbaru berada di index 0 ---
    runs = sorted(runs, key=lambda r: r.start_time, reverse=True)

    if not runs:
        return 'NOT RUN'

    if runs[0].running:
        return 'RUNNING'

    try:
        return str(runs[0].outcome).upper()
    except:
        return 'ABORTED'


monitoring_report = []
processed_scenarios = set()


def classify_scenario(s, layer_code):

    status = get_latest_status_today(s.to_scenario())

    active_scenarios[layer_code].append(s)

    if status in ('SUCCESS', 'WARNING'):
        successful_scenarios[layer_code].append(s)
        status = 'SUCCESS'

    elif status == 'NOT RUN':
        not_run_scenarios[layer_code].append(s)

    elif status == 'ABORTED':
        aborted_scenarios[layer_code].append(s)

    elif status == 'RUNNING':
        running_scenarios[layer_code].append(s)

    else:
        failed_scenarios[layer_code].append(s)
        status = 'FAILED'

    row = {
        'PROJECT_NAME': s['projectKey'],
        'SCENARIO_NAME': s['id'],
        'LAYER': layer_code,
        'STATUS': status
    }

    monitoring_report.append(row)


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

    '''
    # --- SCRIPT LAMA, KITA SUDAH TAK PERLU---
    for s in all_scenarios:
        if s['active'] and scenario_for_layer(layer_code, s['id']):
    '''

    # --- SCRIPT BARU: TANPA FILTER PREFIX SCENARIO ---
    for s in all_scenarios:
        if s['active']:

            # --- Hindari scenario yang terproses lebih dari sekali ---
            scenario_key = (s['projectKey'], s['id'])

            if scenario_key in processed_scenarios:
                continue

            processed_scenarios.add(scenario_key)

            classify_scenario(s, layer_code)


# --- Proses scenario tambahan (manual override) ---
for extra in extra_scenarios:

    try:
        project = client.get_project(extra['project_key'])
        layer_code = extra['layer']

        s_list = project.list_scenarios()
        s = next((x for x in s_list if x['id'] == extra['scenario_id']), None)

        if s is None:
            print(f"$Log: Scenario {extra['scenario_id']} tidak ditemukan di project {extra['project_key']}")
            continue

        if s['active']:

            # --- Hindari duplicate dengan scanning project utama ---
            scenario_key = (s['projectKey'], s['id'])

            if scenario_key in processed_scenarios:
                continue

            processed_scenarios.add(scenario_key)

            classify_scenario(s, layer_code)

    except Exception as e:
        print(f"$Log: Error processing extra scenario {extra['scenario_id']}: {e}")


print(f'$Log: Writing report')


# --- Membentuk DataFrame ---
df = pd.DataFrame(
    monitoring_report,
    columns=[
        'PROJECT_NAME',
        'SCENARIO_NAME',
        'LAYER',
        'STATUS'
    ]
)

# --- Urutan kustom untuk STATUS ---
status_order = ['FAILED', 'SUCCESS', 'RUNNING', 'NOT RUN', 'ABORTED']
df['STATUS'] = pd.Categorical(df['STATUS'], categories=status_order, ordered=True)

# --- Urutan kustom untuk LAYER ---
layer_order = ['T1', 'T2', 'T3']
df['LAYER'] = pd.Categorical(df['LAYER'], categories=layer_order, ordered=True)

#df.sort_values(by=['STATUS', 'LAYER', 'PROJECT_NAME', 'SCENARIO_NAME'], ascending=[True, True, True, True])

df = df.sort_values(
    by=['STATUS', 'LAYER', 'PROJECT_NAME', 'SCENARIO_NAME'],
    ascending=[True, True, True, True]
)



# --- Output dataset ---
output_dataset = dataiku.Dataset("SCENARIO_REPORT_V2")
output_dataset.write_dataframe(df)

print(f'$Log: Total monitored scenarios: {len(df)}')
print(f'$Log: Monitoring report completed')
