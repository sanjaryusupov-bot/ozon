import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import re
import random

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Сборка заказов",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =====================================================================
# ДИЗАЙН-СИСТЕМА
# Тема: "терминал сканера" — тёмный индустриальный интерфейс под работу
# на телефоне в складском освещении. Акцент — сигнальный янтарный цвет
# (как на складской разметке/оборудовании), моноширинный шрифт для
# кодов/баркодов/IMEI, гротеск для интерфейсных надписей.
# =====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600;700&display=swap');

    :root {
        --bg: #1B2027;
        --surface: #242B33;
        --surface-2: #2E3640;
        --accent: #F5A623;
        --accent-dark: #C97F0E;
        --accent-ink: #201503;
        --success: #34B768;
        --success-bg: #17301F;
        --danger: #E5484D;
        --danger-bg: #331A1B;
        --text: #F4F6F8;
        --text-muted: #90A0AA;
        --border: #3A4249;
    }

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', -apple-system, sans-serif !important;
    }

    .stApp {
        background: var(--bg) !important;
        color: var(--text) !important;
    }

    [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; }

    .main > div {
        padding: 0.75rem 0.9rem 6rem 0.9rem !important;
        max-width: 560px;
        margin: 0 auto;
    }

    .block-container { padding-top: 1rem !important; }

    h1 {
        font-size: 26px !important;
        font-weight: 700 !important;
        text-align: center !important;
        color: var(--text) !important;
        letter-spacing: 0.3px;
        margin-bottom: 4px !important;
    }
    h2 {
        font-size: 22px !important;
        font-weight: 700 !important;
        text-align: center !important;
        color: var(--text) !important;
    }
    h3 { font-size: 19px !important; font-weight: 600 !important; color: var(--text) !important; }
    p, div, span, label { color: var(--text); }
    .stCaption, [data-testid="stCaptionContainer"] { color: var(--text-muted) !important; }

    hr, [data-testid="stDivider"] { border-color: var(--border) !important; opacity: 0.6; }

    .time-display {
        text-align: center;
        color: var(--text-muted) !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 14px !important;
        letter-spacing: 0.5px;
        margin: 0 0 10px 0 !important;
        padding: 6px 10px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        display: block;
    }

    .task-counter {
        text-align: center;
        font-size: 16px !important;
        font-weight: 600;
        color: var(--accent-ink) !important;
        margin: 10px 0 16px 0;
        padding: 10px;
        background: var(--accent);
        border-radius: 10px;
        letter-spacing: 0.3px;
    }

    .task-card {
        background: var(--surface);
        border-radius: 14px;
        padding: 16px 16px 14px 16px;
        margin: 10px 0 6px 0;
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        position: relative;
    }
    .task-card b { color: var(--text) !important; }
    .task-card .item-name {
        font-size: 18px !important;
        font-weight: 600;
        color: var(--text) !important;
        display: block;
        margin: 6px 0 10px 0;
    }
    .task-card .place-tag {
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 15px !important;
        font-weight: 700;
        color: var(--accent-ink) !important;
        background: var(--accent);
        padding: 3px 10px;
        border-radius: 6px;
        letter-spacing: 0.5px;
    }
    .chip-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
    .chip {
        font-size: 13px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        color: var(--text-muted) !important;
        background: var(--surface-2);
        border: 1px solid var(--border);
        padding: 4px 9px;
        border-radius: 6px;
    }

    .stButton button, .stDownloadButton button {
        font-size: 18px !important;
        font-weight: 600 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        padding: 16px !important;
        height: 62px !important;
        width: 100% !important;
        border-radius: 12px !important;
        margin: 5px 0 !important;
        transition: transform 0.12s ease, box-shadow 0.12s ease !important;
        letter-spacing: 0.2px;
    }
    .stButton button:active, .stDownloadButton button:active { transform: scale(0.98) !important; }

    .stButton button[kind="primary"], .stDownloadButton button[kind="primary"],
    [data-testid="stBaseButton-primary"] {
        background: var(--accent) !important;
        color: var(--accent-ink) !important;
        border: none !important;
        box-shadow: 0 3px 0 var(--accent-dark) !important;
    }
    .stButton button[kind="primary"]:hover { filter: brightness(1.05); }

    .stButton button[kind="secondary"], .stDownloadButton button[kind="secondary"],
    [data-testid="stBaseButton-secondary"] {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
    }
    .stButton button[kind="secondary"]:hover { border-color: var(--accent) !important; }

    .stTextInput input {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 24px !important;
        font-weight: 600;
        padding: 20px !important;
        height: 68px !important;
        text-align: center !important;
        background: var(--surface-2) !important;
        color: var(--text) !important;
        border: 2px solid var(--border) !important;
        border-radius: 12px !important;
        letter-spacing: 1px;
    }
    .stTextInput input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(245, 166, 35, 0.25) !important;
    }
    .stTextInput label { color: var(--text-muted) !important; font-size: 14px !important; }

    .barcode-label {
        text-align: center;
        color: var(--text-muted) !important;
        font-size: 14px !important;
        margin: 14px 0 6px 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .barcode-display {
        font-size: 34px !important;
        font-weight: 600 !important;
        text-align: center !important;
        font-family: 'IBM Plex Mono', monospace !important;
        letter-spacing: 2px !important;
        color: var(--accent) !important;
        background: #12151A;
        padding: 22px 10px;
        border-radius: 12px;
        margin: 6px 0 16px 0;
        border: 1px solid var(--border);
        position: relative;
        overflow: hidden;
        text-shadow: 0 0 14px rgba(245, 166, 35, 0.45);
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
    }
    .barcode-display::after {
        content: "";
        position: absolute;
        left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--accent), transparent);
        opacity: 0.8;
        animation: scanline 2.4s linear infinite;
    }
    @keyframes scanline {
        0% { top: 0%; }
        50% { top: 100%; }
        100% { top: 0%; }
    }
    .barcode-last4 {
        font-size: 42px !important;
        color: var(--accent-ink) !important;
        background: var(--accent);
        padding: 2px 12px;
        border-radius: 8px;
        text-shadow: none !important;
        box-shadow: 0 0 16px rgba(245, 166, 35, 0.5);
    }

    [data-testid="metric-container"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px;
        padding: 12px 10px !important;
        margin: 5px 0;
        text-align: center;
    }
    [data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 13px !important; }
    [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace !important;
        color: var(--text) !important;
        font-size: 17px !important;
    }

    .stProgress > div > div > div {
        height: 22px !important;
        border-radius: 12px !important;
        background: linear-gradient(90deg, var(--accent-dark), var(--accent)) !important;
    }
    .stProgress > div > div { background: var(--surface-2) !important; border-radius: 12px !important; }

    .scanned-item {
        background: var(--success-bg);
        border-radius: 10px;
        padding: 10px 12px;
        margin: 5px 0;
        border-left: 3px solid var(--success);
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 15px !important;
        color: var(--text) !important;
    }

    .step-dots { display: flex; justify-content: center; gap: 10px; margin: 6px 0 18px 0; }
    .step-dot {
        width: 34px; height: 34px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'IBM Plex Mono', monospace; font-weight: 700; font-size: 15px;
        border: 2px solid var(--border);
        color: var(--text-muted);
        background: var(--surface);
    }
    .step-dot.active { border-color: var(--accent); color: var(--accent-ink); background: var(--accent); }
    .step-dot.done { border-color: var(--success); color: var(--success); background: var(--success-bg); }
    .step-line { width: 28px; height: 2px; background: var(--border); align-self: center; }

    [data-testid="stAlertContainer"] {
        border-radius: 10px !important;
        font-size: 16px !important;
    }

    .emoji-big { font-size: 56px !important; text-align: center; }
    @keyframes celebrate {
        0% { transform: scale(1); } 50% { transform: scale(1.06); } 100% { transform: scale(1); }
    }

    .main > div { padding-bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px)) !important; }
</style>
""", unsafe_allow_html=True)

# --- ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ---
def connect_to_gsheet():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Секрет не найден")
            return None

        creds_dict = dict(st.secrets["gcp_service_account"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_id = "109S4MTu32nb2Ou5JiYEmWxj1urNxLXAc0vZjD5JS-F4"
        return client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"❌ Ошибка: {e}")
        return None

# --- УНИКАЛЬНЫЙ ИДЕНТИФИКАТОР ЗАДАНИЯ ---
def make_task_id(order, article, place):
    return f"{str(order).strip()}|{str(article).strip()}|{str(place).strip()}"

# --- ЗАГРУЗКА ДАННЫХ ---
@st.cache_data(ttl=30)
def load_all_data():
    sh = connect_to_gsheet()
    if sh is None:
        return None, None, None, None, []

    try:
        # Задания
        worksheet_tasks = sh.worksheet("Отбор")
        tasks_data = worksheet_tasks.get_all_values()
        if len(tasks_data) > 1:
            tasks_df = pd.DataFrame(tasks_data[1:], columns=tasks_data[0])
            tasks_df.columns = tasks_df.columns.str.strip()
            tasks_df['Кол-во'] = pd.to_numeric(tasks_df['Кол-во'], errors='coerce').fillna(1).astype(int)
            tasks_df['Артикул/Код OZON'] = tasks_df['Артикул/Код OZON'].astype(str).str.strip()
            tasks_df['Артикул/Код OZON'] = tasks_df['Артикул/Код OZON'].str.replace(r'\.0$', '', regex=True)

            # ВАЖНО: если один и тот же заказ содержит один и тот же артикул
            # на одном и том же месте несколькими строками (например, товар
            # продублирован в исходной таблице) — это не два разных задания,
            # а один и тот же пик с суммарным количеством. Схлопываем такие
            # строки в одну, иначе у заданий совпадают ID и кнопки падают
            # с ошибкой StreamlitDuplicateElementKey.
            # Разные артикулы (разные баркоды) в одном заказе при этом
            # остаются отдельными заданиями — группировка идёт именно по
            # тройке (заказ, артикул, место), а не по одному заказу.
            tasks_df = tasks_df.groupby(
                ['Номер заказа', 'Артикул/Код OZON', 'Место'], as_index=False
            ).agg({
                'Наименование товара': 'first',
                'Кол-во': 'sum'
            })

            # Уникальный ID для каждого задания (заказ+артикул+место)
            tasks_df['task_id'] = tasks_df.apply(
                lambda r: make_task_id(r['Номер заказа'], r['Артикул/Код OZON'], r['Место']),
                axis=1
            )
        else:
            tasks_df = pd.DataFrame(columns=['Номер заказа', 'Артикул/Код OZON', 'Наименование товара', 'Место', 'Кол-во', 'task_id'])

        # Остатки
        worksheet_stock = sh.worksheet("Остатки")
        stock_data = worksheet_stock.get_all_values()
        if len(stock_data) > 1:
            stock_df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
            stock_df.columns = stock_df.columns.str.strip()
            stock_df['Артикул/Код OZON'] = stock_df['Артикул/Код OZON'].astype(str).str.strip()
            stock_df['Артикул/Код OZON'] = stock_df['Артикул/Код OZON'].str.replace(r'\.0$', '', regex=True)
            stock_df['Кол-во'] = pd.to_numeric(stock_df['Кол-во'], errors='coerce')
            stock_df['Имеи'] = stock_df['Имеи'].astype(str).str.lower().str.strip()
        else:
            stock_df = pd.DataFrame(columns=['Место', 'Наименование товара', 'Артикул/Код OZON', 'Кол-во', '№ поставки', '№ ГТД', 'Имеи', 'Длина', 'Ширина', 'Высота', 'вес', 'Имеи1', 'Имеи2'])

        # Справочник
        worksheet_ref = sh.worksheet("Справочник")
        ref_data = worksheet_ref.get_all_values()
        if len(ref_data) > 1:
            ref_df = pd.DataFrame(ref_data[1:], columns=ref_data[0])
            ref_df.columns = ref_df.columns.str.strip()
            ref_df['Артикул/Код OZON'] = ref_df['Артикул/Код OZON'].astype(str).str.strip()
            ref_df['Артикул/Код OZON'] = ref_df['Артикул/Код OZON'].str.replace(r'\.0$', '', regex=True)
            for col in ['Длина', 'Ширина', 'Высота', 'вес']:
                if col in ref_df.columns:
                    ref_df[col] = pd.to_numeric(ref_df[col], errors='coerce')
        else:
            ref_df = pd.DataFrame(columns=['Наименования', 'Артикул/Код OZON', 'Цена', 'Длина', 'Ширина', 'Высота', 'вес'])

        # Лог сканирований
        log_df = None
        completed_task_ids_from_log = []
        try:
            worksheet_log = sh.worksheet("Лог_сканирований")
            log_data = worksheet_log.get_all_values()
            if len(log_data) > 1:
                log_df = pd.DataFrame(log_data[1:], columns=log_data[0])
                log_df.columns = log_df.columns.str.strip()
                required_cols = {'Номер заказа', 'Артикул/Код OZON', 'Место'}
                if required_cols.issubset(set(log_df.columns)):
                    for _, r in log_df.iterrows():
                        tid = make_task_id(r['Номер заказа'], r['Артикул/Код OZON'], r['Место'])
                        completed_task_ids_from_log.append(tid)
                elif 'Номер заказа' in log_df.columns:
                    completed_task_ids_from_log = log_df['Номер заказа'].astype(str).str.strip().tolist()
                completed_task_ids_from_log = [x for x in completed_task_ids_from_log if x and x != 'nan']
        except:
            log_df = pd.DataFrame(columns=['Номер заказа', 'Наименование товара', 'Артикул/Код OZON', 'Кол-во',
                                            '№ поставки', '№ ГТД', 'Длина', 'Ширина', 'Высота', 'вес',
                                            'Имеи1', 'Имеи2', 'Время отбора', 'Место'])

        return tasks_df, stock_df, ref_df, log_df, list(set(completed_task_ids_from_log))
    except Exception as e:
        st.error(f"❌ Ошибка загрузки: {e}")
        return None, None, None, None, []

# --- ПОЛУЧЕНИЕ ТАШКЕНТСКОГО ВРЕМЕНИ ---
def get_tashkent_time():
    tashkent_time = datetime.utcnow() + timedelta(hours=5)
    return tashkent_time.strftime("%Y-%m-%d %H:%M:%S")

# --- ФУНКЦИЯ СОХРАНЕНИЯ В GOOGLE SHEETS ---
def save_to_gsheet(record):
    try:
        sh = connect_to_gsheet()
        if sh is None:
            return False

        clean_record = {}
        for key, value in record.items():
            if value is None or pd.isna(value):
                clean_record[key] = ''
            else:
                clean_record[key] = str(value)

        log_name = "Лог_сканирований"
        try:
            ws = sh.worksheet(log_name)
        except:
            ws = sh.add_worksheet(title=log_name, rows="10000", cols="20")
            headers = ['Номер заказа', 'Наименование товара', 'Артикул/Код OZON',
                      'Кол-во', '№ поставки', '№ ГТД', 'Длина', 'Ширина',
                      'Высота', 'вес', 'Имеи1', 'Имеи2', 'Время отбора', 'Место']
            ws.append_row(headers)

        row = [
            clean_record.get('Номер заказа', ''),
            clean_record.get('Наименование товара', ''),
            clean_record.get('Артикул/Код OZON', ''),
            clean_record.get('Кол-во', ''),
            clean_record.get('№ поставки', ''),
            clean_record.get('№ ГТД', ''),
            clean_record.get('Длина', ''),
            clean_record.get('Ширина', ''),
            clean_record.get('Высота', ''),
            clean_record.get('вес', ''),
            clean_record.get('Имеи1', ''),
            clean_record.get('Имеи2', ''),
            clean_record.get('Время отбора', ''),
            clean_record.get('Место', '')
        ]
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ Ошибка сохранения: {e}")
        return False

# --- ФУНКЦИЯ ПРОВЕРКИ УНИКАЛЬНОСТИ IMEI В ЛОГЕ ---
def check_imei_unique(log_df, order_number, imei1, imei2):
    if log_df is None or log_df.empty:
        return True, ""

    order_logs = log_df[log_df['Номер заказа'].astype(str).str.strip() == str(order_number).strip()]

    if order_logs.empty:
        return True, ""

    existing_imeis = []
    for _, row in order_logs.iterrows():
        if pd.notna(row.get('Имеи1', '')) and str(row.get('Имеи1', '')).strip() != '':
            existing_imeis.append(str(row.get('Имеи1', '')).strip())
        if pd.notna(row.get('Имеи2', '')) and str(row.get('Имеи2', '')).strip() != '':
            existing_imeis.append(str(row.get('Имеи2', '')).strip())

    if imei1 and imei1 != '0' and imei1 in existing_imeis:
        return False, f"IMEI {imei1} уже используется для заказа {order_number}"
    if imei2 and imei2 != '0' and imei2 in existing_imeis:
        return False, f"IMEI {imei2} уже используется для заказа {order_number}"

    return True, ""

# --- ФУНКЦИИ ПОИСКА ---
def find_stock_by_place_and_article(stock_df, place, article):
    """Ищет товар в остатках по месту и артикулу одновременно"""
    try:
        if stock_df is None or stock_df.empty:
            return None
        items = stock_df[
            (stock_df['Место'].astype(str).str.strip() == str(place).strip()) &
            (stock_df['Артикул/Код OZON'].astype(str).str.strip() == str(article).strip())
        ]
        return items.iloc[0] if not items.empty else None
    except:
        return None

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ ---
if 'tasks_df' not in st.session_state:
    st.session_state.tasks_df = None
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = None
if 'log_df' not in st.session_state:
    st.session_state.log_df = None
if 'step' not in st.session_state:
    st.session_state.step = 'main'
if 'current_task' not in st.session_state:
    st.session_state.current_task = None
if 'current_task_id' not in st.session_state:
    st.session_state.current_task_id = None
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = None
if 'scanned_items' not in st.session_state:
    st.session_state.scanned_items = []
if 'imeis' not in st.session_state:
    st.session_state.imeis = []
if 'completed' not in st.session_state:
    st.session_state.completed = []
if 'cell_number' not in st.session_state:
    st.session_state.cell_number = ""
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'completed_task_ids' not in st.session_state:
    st.session_state.completed_task_ids = []
if 'order_completed' not in st.session_state:
    st.session_state.order_completed = False

# --- ЗАГРУЗКА ДАННЫХ ---
if not st.session_state.data_loaded:
    with st.spinner("Загрузка данных..."):
        tasks, stock, ref, log, completed = load_all_data()
        if tasks is not None:
            st.session_state.tasks_df = tasks
            st.session_state.stock_df = stock
            st.session_state.log_df = log
            st.session_state.completed_task_ids = completed
            st.session_state.data_loaded = True

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state.step == 'main':
    st.title("📦 Сборка заказов")

    st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄", use_container_width=True):
            st.session_state.data_loaded = False
            st.cache_data.clear()
            st.rerun()

    st.divider()

    if st.session_state.tasks_df is not None and not st.session_state.tasks_df.empty:
        completed_from_log = st.session_state.completed_task_ids
        completed_from_session = [c.get('task_id') for c in st.session_state.completed]
        all_completed = list(set(completed_from_log + completed_from_session))

        active_tasks = st.session_state.tasks_df[~st.session_state.tasks_df['task_id'].isin(all_completed)]

        if not active_tasks.empty:
            st.subheader("📋 Активные задания")

            st.markdown(f'<div class="task-counter">📌 Осталось заданий: {len(active_tasks)}</div>', unsafe_allow_html=True)

            for idx, row in active_tasks.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="task-card">
                        <span class="place-tag">📍 {row['Место']}</span>
                        <span class="item-name">{row['Наименование товара']}</span>
                        <div class="chip-row">
                            <span class="chip">Заказ {row['Номер заказа']}</span>
                            <span class="chip">Кол-во {row['Кол-во']}</span>
                            <span class="chip">Арт. {row['Артикул/Код OZON']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"▶️ Взять в работу", key=f"btn_{row['task_id']}_{idx}", use_container_width=True, type="primary"):
                        st.session_state.cell_number = row['Место']
                        # ВАЖНО: используем именно нажатую строку (row), а не повторный
                        # поиск по "Место" — иначе при двух разных баркодах в одной
                        # ячейке всегда открывалась бы первая позиция.
                        stock = find_stock_by_place_and_article(
                            st.session_state.stock_df,
                            row['Место'],
                            row['Артикул/Код OZON']
                        )
                        if stock is not None:
                            st.session_state.current_task = row
                            st.session_state.current_task_id = row['task_id']
                            st.session_state.current_stock = stock
                            st.session_state.scanned_items = []
                            st.session_state.imeis = []
                            st.session_state.order_completed = False
                            st.session_state.step = 'scan'
                            st.rerun()
                        else:
                            st.error(f"❌ Товар с артикулом {row['Артикул/Код OZON']} не найден на месте {row['Место']}")
        else:
            st.markdown("""
            <div style="text-align: center; padding: 40px 20px;">
                <div class="emoji-big">🎉</div>
                <h2 style="color: var(--success);">Все задания выполнены!</h2>
                <p style="font-size: 18px; color: var(--text);">Отличная работа! 👏</p>
                <p style="font-size: 15px; color: var(--text-muted);">Вы собрали все заказы</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("📊 Показать отчет", use_container_width=True, type="primary"):
                st.session_state.step = 'report'
                st.rerun()
    else:
        st.warning("⚠️ Нет заданий")
        if st.button("🔄 Загрузить данные", use_container_width=True, type="primary"):
            st.session_state.data_loaded = False
            st.cache_data.clear()
            st.rerun()

# --- СКАНИРОВАНИЕ ---
elif st.session_state.step == 'scan':
    task = st.session_state.current_task
    stock = st.session_state.current_stock

    if task is None:
        st.error("Ошибка")
        if st.button("🔙 Назад"):
            st.session_state.step = 'main'
            st.rerun()
    else:
        st.markdown(f'<div class="barcode-label">📍 Место</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="barcode-display">{task["Место"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 Товар", task['Наименование товара'][:25] + "...")
        with col2:
            st.metric("📱 Артикул", task['Артикул/Код OZON'])

        # Показываем баркод — LED-панель сканера
        barcode_full = str(task['Артикул/Код OZON']).strip()
        st.markdown(f'<div class="barcode-label">📷 Сканируйте баркод</div>', unsafe_allow_html=True)

        if len(barcode_full) >= 4:
            barcode_first = barcode_full[:-4]
            barcode_last4 = barcode_full[-4:]
            st.markdown(f"""
            <div class="barcode-display">
                {barcode_first}<span class="barcode-last4">{barcode_last4}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="barcode-display">{barcode_full}</div>
            """, unsafe_allow_html=True)

        total = int(task['Кол-во'])
        scanned_count = len(st.session_state.scanned_items)

        st.progress(scanned_count / total if total > 0 else 0)
        st.caption(f"📊 Отсканировано: {scanned_count} из {total}")

        if st.session_state.scanned_items:
            st.write("**✅ Отсканированные баркоды:**")
            for i, item in enumerate(st.session_state.scanned_items, 1):
                st.markdown(f'<div class="scanned-item">#{i}  {item}  ✅</div>', unsafe_allow_html=True)

        barcode = st.text_input("📷 Введите баркод", placeholder="Наведите сканер...", key="barcode_input")

        def build_record(imei1='', imei2=''):
            return {
                'task_id': st.session_state.current_task_id,
                'Номер заказа': str(task['Номер заказа']),
                'Наименование товара': str(task['Наименование товара']),
                'Артикул/Код OZON': str(task['Артикул/Код OZON']),
                'Кол-во': str(task['Кол-во']),
                '№ поставки': str(stock.get('№ поставки', '')) if stock is not None else '',
                '№ ГТД': str(stock.get('№ ГТД', '')) if stock is not None else '',
                'Длина': str(stock.get('Длина', '')) if stock is not None else '',
                'Ширина': str(stock.get('Ширина', '')) if stock is not None else '',
                'Высота': str(stock.get('Высота', '')) if stock is not None else '',
                'вес': str(stock.get('вес', '')) if stock is not None else '',
                'Имеи1': imei1,
                'Имеи2': imei2,
                'Время отбора': get_tashkent_time(),
                'Место': str(st.session_state.cell_number)
            }

        if barcode:
            expected_barcode = str(task['Артикул/Код OZON']).strip()
            if barcode.strip() == expected_barcode:
                if barcode not in st.session_state.scanned_items:
                    st.session_state.scanned_items.append(barcode)
                    st.success(f"✅ Баркод принят! ({len(st.session_state.scanned_items)}/{total})")

                    if len(st.session_state.scanned_items) >= total:
                        if stock is not None and stock.get('Имеи', '').lower() == 'да':
                            st.session_state.imeis = []
                            st.session_state.step = 'imei'
                            st.rerun()
                        else:
                            record = build_record()
                            if save_to_gsheet(record):
                                st.session_state.completed.append(record)
                                st.session_state.completed_task_ids.append(st.session_state.current_task_id)
                                st.session_state.order_completed = True
                                st.session_state.step = 'finish'
                                st.rerun()
                            else:
                                st.error("❌ Ошибка сохранения. Попробуйте еще раз.")
                    else:
                        st.rerun()
                else:
                    st.warning("⚠️ Этот баркод уже отсканирован!")
            else:
                st.error("❌ Неверный баркод!")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Назад", use_container_width=True):
                st.session_state.step = 'main'
                st.rerun()
        with col2:
            if scanned_count >= total:
                if st.button("✅ Завершить сборку", use_container_width=True, type="primary"):
                    if stock is not None and stock.get('Имеи', '').lower() == 'да':
                        st.session_state.imeis = []
                        st.session_state.step = 'imei'
                        st.rerun()
                    else:
                        record = build_record()
                        if save_to_gsheet(record):
                            st.session_state.completed.append(record)
                            st.session_state.completed_task_ids.append(st.session_state.current_task_id)
                            st.session_state.order_completed = True
                            st.session_state.step = 'finish'
                            st.rerun()
                        else:
                            st.error("❌ Ошибка сохранения. Попробуйте еще раз.")

# --- ВВОД IMEI ---
elif st.session_state.step == 'imei':
    stock = st.session_state.current_stock
    task = st.session_state.current_task

    st.subheader(f"📱 Введите IMEI")
    st.write(f"**{task['Наименование товара']}**")
    st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)

    current = len(st.session_state.imeis)

    dot1_cls = "done" if current >= 1 else "active"
    dot2_cls = "done" if current >= 2 else ("active" if current == 1 else "")
    st.markdown(f"""
    <div class="step-dots">
        <div class="step-dot {dot1_cls}">1</div>
        <div class="step-line"></div>
        <div class="step-dot {dot2_cls}">2</div>
    </div>
    """, unsafe_allow_html=True)

    if current == 0:
        st.write("**Введите IMEI 1**")
        label = "IMEI 1"
        placeholder = "Введите 15 цифр"
        st.info("ℹ️ Введите первый IMEI (15 цифр)")

        imei_input = st.text_input(label, placeholder=placeholder, key="imei1_input")

        if imei_input:
            if re.match(r'^\d{15}$', imei_input):
                is_unique, msg = check_imei_unique(
                    st.session_state.log_df,
                    task['Номер заказа'],
                    imei_input,
                    ''
                )
                if is_unique:
                    st.session_state.imeis.append(imei_input)
                    st.success(f"✅ IMEI 1 сохранен")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.error("❌ Введите 15 цифр")

        if st.button("🔙 Назад", use_container_width=True):
            st.session_state.step = 'scan'
            st.rerun()

    elif current == 1:
        st.write("**Введите IMEI 2 (или 0, если нет)**")
        label = "IMEI 2"
        placeholder = "Введите 15 цифр или 0"
        st.info("ℹ️ Введите второй IMEI (15 цифр) или 0, если его нет")

        imei_input = st.text_input(label, placeholder=placeholder, key="imei2_input")

        if imei_input:
            if imei_input == '0' or re.match(r'^\d{15}$', imei_input):
                first_imei = st.session_state.imeis[0]
                if imei_input != '0' and imei_input == first_imei:
                    st.error("❌ IMEI не могут быть одинаковыми! Введите другой IMEI.")
                else:
                    is_unique, msg = check_imei_unique(
                        st.session_state.log_df,
                        task['Номер заказа'],
                        first_imei,
                        imei_input if imei_input != '0' else ''
                    )
                    if is_unique:
                        st.session_state.imeis.append(imei_input)
                        st.success(f"✅ IMEI 2 сохранен")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
            else:
                st.error("❌ Введите 15 цифр или 0")

        if st.button("🔙 Назад", use_container_width=True):
            st.session_state.step = 'scan'
            st.rerun()

    else:
        imei1 = st.session_state.imeis[0] if len(st.session_state.imeis) > 0 else ''
        imei2 = st.session_state.imeis[1] if len(st.session_state.imeis) > 1 else ''
        imei2_final = '' if imei2 == '0' else imei2

        record = {
            'task_id': st.session_state.current_task_id,
            'Номер заказа': str(task['Номер заказа']),
            'Наименование товара': str(task['Наименование товара']),
            'Артикул/Код OZON': str(task['Артикул/Код OZON']),
            'Кол-во': str(task['Кол-во']),
            '№ поставки': str(stock.get('№ поставки', '')) if stock is not None else '',
            '№ ГТД': str(stock.get('№ ГТД', '')) if stock is not None else '',
            'Длина': str(stock.get('Длина', '')) if stock is not None else '',
            'Ширина': str(stock.get('Ширина', '')) if stock is not None else '',
            'Высота': str(stock.get('Высота', '')) if stock is not None else '',
            'вес': str(stock.get('вес', '')) if stock is not None else '',
            'Имеи1': imei1,
            'Имеи2': imei2_final,
            'Время отбора': get_tashkent_time(),
            'Место': str(st.session_state.cell_number)
        }

        if save_to_gsheet(record):
            st.success("✅ Данные сохранены в Google Sheets!")
            st.session_state.completed.append(record)
            st.session_state.completed_task_ids.append(st.session_state.current_task_id)
            st.session_state.order_completed = True
            st.session_state.step = 'finish'
            st.rerun()
        else:
            st.error("❌ Ошибка сохранения. Попробуйте еще раз.")

        if st.button("🔙 Назад к сканированию", use_container_width=True):
            st.session_state.step = 'scan'
            st.rerun()

# --- ЗАВЕРШЕНИЕ ---
elif st.session_state.step == 'finish':
    task = st.session_state.current_task

    emojis = ['🎉', '✨', '⭐', '🌟', '💫', '🎊', '🏆', '🥇']
    selected_emojis = random.sample(emojis, 4)

    st.markdown(f"""
    <div style="text-align: center; padding: 24px 20px;">
        <div style="font-size: 64px; animation: celebrate 0.5s ease 3;">
            {selected_emojis[0]} {selected_emojis[1]}
            <br>
            {selected_emojis[2]} {selected_emojis[3]}
        </div>
        <h2 style="color: var(--success); margin-top: 16px;">✅ Задание выполнено!</h2>
        <div style="font-size: 20px; margin: 10px 0; color: var(--text);">
            🎯 {task['Наименование товара']}
        </div>
        <div style="font-size: 16px; color: var(--text-muted);">
            📦 Заказ: {task['Номер заказа']}
        </div>
        <div style="font-size: 13px; color: var(--text-muted); margin-top: 8px; font-family: 'IBM Plex Mono', monospace;">
            🕐 {get_tashkent_time()}
        </div>
    </div>
    """, unsafe_allow_html=True)

    total_tasks = len(st.session_state.tasks_df) if st.session_state.tasks_df is not None else 0
    done_tasks = len(set(st.session_state.completed_task_ids))
    remaining = max(total_tasks - done_tasks, 0)

    st.markdown(f"""
    <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 18px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div>
                <div style="font-size: 28px; font-weight: 700; color: var(--success); font-family: 'IBM Plex Mono', monospace;">{done_tasks}</div>
                <div style="font-size: 14px; color: var(--text-muted);">✅ Выполнено</div>
            </div>
            <div>
                <div style="font-size: 28px; font-weight: 700; color: var(--accent); font-family: 'IBM Plex Mono', monospace;">{remaining}</div>
                <div style="font-size: 14px; color: var(--text-muted);">📋 Осталось</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Следующее", use_container_width=True, type="primary"):
            st.session_state.step = 'main'
            st.session_state.current_task = None
            st.session_state.current_task_id = None
            st.session_state.current_stock = None
            st.session_state.scanned_items = []
            st.session_state.imeis = []
            st.session_state.order_completed = False
            st.rerun()
    with col2:
        if st.button("📊 Отчет", use_container_width=True):
            st.session_state.step = 'report'
            st.rerun()

# --- ОТЧЕТ ---
elif st.session_state.step == 'report':
    st.title("📊 Отчет")
    st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)

    if st.session_state.completed:
        df = pd.DataFrame(st.session_state.completed)
        display_cols = [c for c in df.columns if c != 'task_id']
        st.dataframe(df[display_cols], use_container_width=True)

        csv = df[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Скачать отчет",
            csv,
            f"отчет_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv",
            use_container_width=True,
            type="primary"
        )

        st.caption(f"✅ Всего выполнено: {len(df)} заданий")
    else:
        st.info("📭 Нет выполненных заданий")

    if st.button("🔙 На главную", use_container_width=True):
        st.session_state.step = 'main'
        st.rerun()
