
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

today = datetime.now(tz).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)


'''
SCRIPT LAMA -- TIDAK DIPAKAI:

def scenario_for_layer(layer, id):
    if layer == 'T1':
        return id.startswith('EXEC_SC')
    if layer == 'T2' or layer == 'T3':
        return id.startswith('TRIGGER_EXEC_SC')
    raise Exception('Invalid layer')
'''


# ==========================================
# GET LATEST STATUS TODAY
# ==========================================

'''
SCRIPT LAMA:

def get_latest_status_today(scenario):
    runs = [
        r for r in scenario.get_last_runs()
        if r.start_time >= today
    ]

    runs = sorted(runs, key=lambda r: r.start_time, reverse=True)

    if not runs:
        return 'NOT RUN'

    if runs[0].running:
        return 'RUNNING'

    try:
        return str(runs[0].outcome).upper()
    except:
        return 'ABORTED'
'''


# SCRIPT BARU:
# Mengembalikan status dan latest run

def get_latest_status_today(scenario):

    runs = [
        r for r in scenario.get_last_runs()
        if r.start_time >= today
    ]

    runs = sorted(
        runs,
        key=lambda r: r.start_time,
        reverse=True
    )

    if not runs:
        return 'NOT RUN', None

    latest_run = runs[0]

    if latest_run.running:
        return 'RUNNING', latest_run

    try:
        return str(latest_run.outcome).upper(), latest_run

    except:
        return 'ABORTED', latest_run


# ==========================================
# GET RUN DIAGNOSTICS
# ==========================================

def get_run_diagnostics(run):

    diagnostics = {
        'steps': [],
        'messages': []
    }

    if run is None:
        return diagnostics

    try:

        details = run.get_details()

        step_runs = details.get('stepRuns', [])

        for step in step_runs:

            step_info = step.get('step', {})
            result = step.get('result', {})

            step_name = (
                step_info.get('name')
                or step_info.get('id')
                or 'UNKNOWN_STEP'
            )

            step_id = step_info.get('id')

            step_outcome = str(
                result.get('outcome', '')
            ).upper()

            thrown = result.get('thrown', '')

            if isinstance(thrown, dict):
                thrown = ' '.join(
                    str(v) for v in thrown.values()
                )

            step_message = str(thrown) if thrown else ''

            log_message = ''

            if step_id:

                try:
                    log_message = run.get_log(
                        step_id=step_id
                    )

                except Exception:
                    log_message = ''

            diagnostics['steps'].append({
                'name': step_name,
                'outcome': step_outcome,
                'message': step_message,
                'log': str(log_message)
            })

            if step_message:
                diagnostics['messages'].append(step_message)

            if log_message:
                diagnostics['messages'].append(
                    str(log_message)
                )

    except Exception as e:

        print(
            f"$Log: Unable to retrieve run diagnostics: {e}"
        )

    return diagnostics


# ==========================================
# CLASSIFY ERROR
# ==========================================

def classify_error(error_message):

    if not error_message:
        return 'UNKNOWN_ERROR'

    error = str(error_message).upper()

    # Urutan pengecekan penting:
    # Kategori yang lebih spesifik diperiksa terlebih dahulu.

    if any(x in error for x in [
        'TIMEOUT',
        'TIMED OUT',
        'DEADLINE EXCEEDED'
    ]):
        return 'TIMEOUT'

    elif any(x in error for x in [
        'PERMISSION DENIED',
        'ACCESS DENIED',
        'UNAUTHORIZED',
        'FORBIDDEN'
    ]):
        return 'PERMISSION_ERROR'

    elif any(x in error for x in [
        'CONNECTION REFUSED',
        'CONNECTION ERROR',
        'CONNECTION RESET',
        'CONNECTION TIMEOUT',
        'CONNECTION FAILED',
        'NETWORK ERROR'
    ]):
        return 'CONNECTION_ERROR'

    elif any(x in error for x in [
        'ORA-',
        'SQL ERROR',
        'SQL EXCEPTION',
        'SQL SYNTAX',
        'JDBC',
        'DATABASE ERROR'
    ]):
        return 'SQL_ERROR'

    elif any(x in error for x in [
        'PYTHON ERROR',
        'PYTHON EXCEPTION',
        'TRACEBACK',
        'MODULENOTFOUNDERROR',
        'IMPORTERROR'
    ]):
        return 'PYTHON_ERROR'

    elif any(x in error for x in [
        'DATASET NOT FOUND',
        'DATASET ERROR',
        'SCHEMA MISMATCH',
        'COLUMN NOT FOUND',
        'UNKNOWN DATASET'
    ]):
        return 'DATASET_ERROR'

    elif 'RECIPE' in error:
        return 'RECIPE_ERROR'

    return 'UNKNOWN_ERROR'


# ==========================================
# CLASSIFY ABORT
# ==========================================

def classify_abort(error_message):

    if not error_message:
        return 'UNKNOWN_ABORT'

    error = str(error_message).upper()

    if any(x in error for x in [
        'TIMEOUT',
        'TIMED OUT',
        'DEADLINE EXCEEDED'
    ]):
        return 'TIMEOUT'

    elif any(x in error for x in [
        'MANUALLY ABORTED',
        'ABORTED BY USER',
        'ABORT REQUESTED',
        'USER REQUESTED ABORT',
        'CANCELLED BY USER',
        'CANCELED BY USER'
    ]):
        return 'MANUALLY_ABORTED'

    elif any(x in error for x in [
        'INTERRUPTED',
        'SCENARIO INTERRUPTED',
        'EXECUTION INTERRUPTED'
    ]):
        return 'SCENARIO_INTERRUPTED'

    return 'UNKNOWN_ABORT'


# ==========================================
# GET DESCRIPTION
# ==========================================

def get_description(status, run):

    if status in ('SUCCESS', 'WARNING'):

        if status == 'SUCCESS':
            return None

    elif status not in ('FAILED', 'ABORTED'):
        return None

    diagnostics = get_run_diagnostics(run)

    # Gabungkan pesan dari step dan log
    all_messages = ' '.join(
        diagnostics['messages']
    )

    if status == 'WARNING':

        warning_messages = []

        for step in diagnostics['steps']:

            if step['outcome'] != 'WARNING':
                continue

            message = step['message']

            # Jika thrown kosong, cari informasi warning di log
            if not message and step['log']:

                warning_lines = [
                    line.strip()
                    for line in step['log'].splitlines()
                    if any(x in line.upper() for x in [
                        'WARN',
                        'WARNING'
                    ])
                ]

                message = ' | '.join(
                    warning_lines[-3:]
                )

            if message:
                warning_messages.append(
                    f"{step['name']}: {message}"
                )

        if warning_messages:

            return (
                'WARNING = '
                + ' | '.join(warning_messages)
            )[:1000]

        return 'WARNING = Detail warning tidak tersedia'

    elif status == 'FAILED':

        return classify_error(all_messages)

    elif status == 'ABORTED':

        return classify_abort(all_messages)

    return None


# ==========================================
# MONITORING REPORT
# ==========================================

monitoring_report = []
processed_scenarios = set()


# ==========================================
# CLASSIFY SCENARIO
# ==========================================

'''
SCRIPT LAMA:

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
'''


# SCRIPT BARU:

def classify_scenario(s, layer_code):

    original_status, latest_run = get_latest_status_today(
        s.to_scenario()
    )

    status = original_status

    description = get_description(
        original_status,
        latest_run
    )

    active_scenarios[layer_code].append(s)

    if status in ('SUCCESS', 'WARNING'):

        successful_scenarios[layer_code].append(s)

        # WARNING tetap dinormalisasi menjadi SUCCESS
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
        'STATUS': status,
        'DESCRIPTION': description
    }

    monitoring_report.append(row)


# ==========================================
# INITIALIZE DATAIKU CLIENT
# ==========================================

client = dataiku.api_client()
all_project = client.list_project_keys()


# ==========================================
# GET LAYER CODE
# ==========================================

def get_layer_code(layer):

    if layer.startswith('RAW_'):
        return 'T1'

    if layer.startswith('RFD_'):
        return 'T2'

    if layer.startswith('BUS_'):
        return 'T3'

    return ''


# ==========================================
# MAIN SCENARIO SCANNING
# ==========================================

for p in all_project:

    if not (
        p.startswith('RAW_')
        or p.startswith('RFD_')
        or p.startswith('BUS_')
    ):
        continue

    layer_code = get_layer_code(p)

    project = client.get_project(p)
    all_scenarios = project.list_scenarios()

    '''
    SCRIPT LAMA, KITA SUDAH TAK PERLU:

    for s in all_scenarios:
        if s['active'] and scenario_for_layer(layer_code, s['id']):
    '''

    # SCRIPT BARU: TANPA FILTER PREFIX SCENARIO

    for s in all_scenarios:

        if s['active']:

            # Hindari scenario yang terproses lebih dari sekali
            scenario_key = (
                s['projectKey'],
                s['id']
            )

            if scenario_key in processed_scenarios:
                continue

            processed_scenarios.add(scenario_key)

            classify_scenario(s, layer_code)


# ==========================================
# EXTRA SCENARIO (MANUAL OVERRIDE)
# ==========================================

for extra in extra_scenarios:

    try:

        project = client.get_project(
            extra['project_key']
        )

        layer_code = extra['layer']

        s_list = project.list_scenarios()

        s = next(
            (
                x for x in s_list
                if x['id'] == extra['scenario_id']
            ),
            None
        )

        if s is None:

            print(
                f"$Log: Scenario {extra['scenario_id']} "
                f"tidak ditemukan di project {extra['project_key']}"
            )

            continue

        if s['active']:

            # Hindari duplicate dengan scanning project utama
            scenario_key = (
                s['projectKey'],
                s['id']
            )

            if scenario_key in processed_scenarios:
                continue

            processed_scenarios.add(scenario_key)

            classify_scenario(s, layer_code)

    except Exception as e:

        print(
            f"$Log: Error processing extra scenario "
            f"{extra['scenario_id']}: {e}"
        )


print('$Log: Writing report')


# ==========================================
# CREATE DATAFRAME
# ==========================================

df = pd.DataFrame(
    monitoring_report,
    columns=[
        'PROJECT_NAME',
        'SCENARIO_NAME',
        'LAYER',
        'STATUS',
        'DESCRIPTION'
    ]
)


# ==========================================
# CUSTOM STATUS ORDER
# ==========================================

status_order = [
    'FAILED',
    'SUCCESS',
    'RUNNING',
    'NOT RUN',
    'ABORTED'
]

df['STATUS'] = pd.Categorical(
    df['STATUS'],
    categories=status_order,
    ordered=True
)


# ==========================================
# CUSTOM LAYER ORDER
# ==========================================

layer_order = [
    'T1',
    'T2',
    'T3'
]

df['LAYER'] = pd.Categorical(
    df['LAYER'],
    categories=layer_order,
    ordered=True
)


# ==========================================
# SORT DATAFRAME
# ==========================================

'''
SCRIPT LAMA:

df.sort_values(
    by=['STATUS', 'LAYER', 'PROJECT_NAME', 'SCENARIO_NAME'],
    ascending=[True, True, True, True]
)
'''

# SCRIPT BARU:

df = df.sort_values(
    by=[
        'STATUS',
        'LAYER',
        'PROJECT_NAME',
        'SCENARIO_NAME'
    ],
    ascending=[
        True,
        True,
        True,
        True
    ]
)


# ==========================================
# OUTPUT DATASET
# ==========================================

output_dataset = dataiku.Dataset(
    "SCENARIO_REPORT_V2"
)

output_dataset.write_dataframe(df)


# ==========================================
# LOGGING
# ==========================================

print(
    f'$Log: Total monitored scenarios: {len(df)}'
)

print(
    f'$Log: Monitoring report completed'
)
