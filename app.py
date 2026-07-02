import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import re
import time
import random

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Сборка заказов", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- СКРЫВАЕМ БОКОВУЮ ПАНЕЛЬ ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    .main > div {
        padding: 1rem 0.5rem !important;
    }
    .stTextInput input {
        font-size: 28px !important;
        padding: 25px !important;
        height: 80px !important;
        text-align: center !important;
    }
    .stButton button {
        font-size: 28px !important;
        padding: 20px !important;
        height: 70px !important;
        width: 100% !important;
        border-radius: 15px !important;
        margin: 5px 0 !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }
    /* Увеличенный шрифт для баркода */
    .barcode-display {
        font-size: 42px !important;
        font-weight: bold !important;
        text-align: center !important;
        font-family: 'Courier New', monospace !important;
        letter-spacing: 2px !important;
        background: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 2px solid #ddd;
    }
    .barcode-last4 {
        font-size: 52px !important;
        color: #4CAF50 !important;
        background: #e8f5e9;
        padding: 2px 10px;
        border-radius: 8px;
        border: 2px solid #4CAF50;
    }
    .barcode-label {
        text-align: center;
        color: #666;
        font-size: 18px !important;
        margin: 5px 0;
    }
    h1 { font-size: 36px !important; text-align: center !important; }
    h2 { font-size: 30px !important; text-align: center !important; }
    h3 { font-size: 26px !important; text-align: center !important; }
    p, div, span, label { font-size: 22px !important; }
    [data-testid="metric-container"] {
        background: #f0f2f6;
        border-radius: 15px;
        padding: 15px;
        margin: 5px 0;
        text-align: center;
    }
    .stProgress > div > div {
        height: 30px !important;
        border-radius: 15px !important;
    }
    .task-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 5px solid #4CAF50;
    }
    .task-card-done {
        background: #f0f8f0;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border-left: 5px solid #888;
        opacity: 0.5;
        display: none !important;
    }
    .task-card-log {
        background: #fff3e0;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 5px solid #FF9800;
        display: none !important;
    }
    .time-display {
        text-align: center;
        color: #666;
        font-size: 18px !important;
        margin: 5px 0;
    }
    /* Анимация завершения */
    @keyframes celebrate {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .celebration {
        animation: celebrate 0.5s ease 3;
        font-size: 32px !important;
        text-align: center;
        padding: 20px;
    }
    .emoji-big {
        font-size: 64px !important;
        text-align: center;
    }
    /* Счетчик заданий */
    .task-counter {
        text-align: center;
        font-size: 24px !important;
        color: #666;
        margin: 10px 0;
        padding: 10px;
        background: #f8f9fa;
        border-radius: 10px;
    }
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

# --- ЗАГРУЗКА ДАННЫХ ---
@st.cache_data(ttl=30)
def load_all_data():
    sh = connect_to_gsheet()
    if sh is None:
        return None, None, None, None
    
    try:
        # Задания
        worksheet_tasks = sh.worksheet("Отбор")
        tasks_data = worksheet_tasks.get_all_values()
        if len(tasks_data) > 1:
            tasks_df = pd.DataFrame(tasks_data[1:], columns=tasks_data[0])
            tasks_df.columns = tasks_df.columns.str.strip()
            tasks_df['Кол-во'] = pd.to_numeric(tasks_df['Кол-во'], errors='coerce').fillna(1).astype(int)
            tasks_df['Артикул/Код OZON'] = tasks_df['Артикул/Код OZON'].astype(str).str.replace('.0', '', regex=False).str.strip()
        else:
            tasks_df = pd.DataFrame(columns=['Номер заказа', 'Артикул/Код OZON', 'Наименование товара', 'Место', 'Кол-во'])
        
        # Остатки
        worksheet_stock = sh.worksheet("Остатки")
        stock_data = worksheet_stock.get_all_values()
        if len(stock_data) > 1:
            stock_df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
            stock_df.columns = stock_df.columns.str.strip()
            stock_df['Артикул/Код OZON'] = stock_df['Артикул/Код OZON'].astype(str).str.replace('.0', '', regex=False).str.strip()
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
            ref_df['Артикул/Код OZON'] = ref_df['Артикул/Код OZON'].astype(str).str.replace('.0', '', regex=False).str.strip()
            for col in ['Длина', 'Ширина', 'Высота', 'вес']:
                if col in ref_df.columns:
                    ref_df[col] = pd.to_numeric(ref_df[col], errors='coerce')
        else:
            ref_df = pd.DataFrame(columns=['Наименования', 'Артикул/Код OZON', 'Цена', 'Длина', 'Ширина', 'Высота', 'вес'])
        
        # Лог сканирований
        log_df = None
        try:
            worksheet_log = sh.worksheet("Лог_сканирований")
            log_data = worksheet_log.get_all_values()
            if len(log_data) > 1:
                log_df = pd.DataFrame(log_data[1:], columns=log_data[0])
                log_df.columns = log_df.columns.str.strip()
        except:
            log_df = pd.DataFrame(columns=['Номер заказа', 'Имеи1', 'Имеи2'])
        
        return tasks_df, stock_df, ref_df, log_df
    except Exception as e:
        st.error(f"❌ Ошибка загрузки: {e}")
        return None, None, None, None

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

# --- ФУНКЦИЯ ПОЛУЧЕНИЯ ВЫПОЛНЕННЫХ ЗАКАЗОВ ---
def get_completed_orders(log_df):
    if log_df is None or log_df.empty:
        return []
    
    completed = []
    for _, row in log_df.iterrows():
        order = str(row.get('Номер заказа', '')).strip()
        if order and order != '' and order != 'nan':
            completed.append(order)
    
    return list(set(completed))

# --- ФУНКЦИИ ПОИСКА ---
def find_task(tasks_df, cell):
    try:
        if tasks_df is None or tasks_df.empty:
            return None
        task = tasks_df[tasks_df['Место'].astype(str).str.strip() == str(cell).strip()]
        return task.iloc[0] if not task.empty else None
    except:
        return None

def find_stock(stock_df, article):
    try:
        if stock_df is None or stock_df.empty:
            return None
        items = stock_df[stock_df['Артикул/Код OZON'].astype(str).str.strip() == str(article).strip()]
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
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = None
if 'scanned' not in st.session_state:
    st.session_state.scanned = []
if 'imeis' not in st.session_state:
    st.session_state.imeis = []
if 'completed' not in st.session_state:
    st.session_state.completed = []
if 'cell_number' not in st.session_state:
    st.session_state.cell_number = ""
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'barcode_scanned' not in st.session_state:
    st.session_state.barcode_scanned = False
if 'completed_orders' not in st.session_state:
    st.session_state.completed_orders = []
if 'celebration_show' not in st.session_state:
    st.session_state.celebration_show = False

# --- ЗАГРУЗКА ДАННЫХ ---
if not st.session_state.data_loaded:
    with st.spinner("Загрузка данных..."):
        tasks, stock, ref, log = load_all_data()
        if tasks is not None:
            st.session_state.tasks_df = tasks
            st.session_state.stock_df = stock
            st.session_state.log_df = log
            st.session_state.completed_orders = get_completed_orders(log)
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
        # Получаем список выполненных заказов из лога и сессии
        completed_from_log = st.session_state.completed_orders
        completed_from_session = [c.get('Номер заказа') for c in st.session_state.completed]
        all_completed = list(set(completed_from_log + completed_from_session))
        
        # Фильтруем только активные задания (не выполненные)
        active_tasks = st.session_state.tasks_df[~st.session_state.tasks_df['Номер заказа'].isin(all_completed)]
        
        if not active_tasks.empty:
            st.subheader("📋 Активные задания")
            
            # Показываем счетчик
            st.markdown(f'<div class="task-counter">📌 Осталось заданий: {len(active_tasks)}</div>', unsafe_allow_html=True)
            
            for idx, row in active_tasks.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="task-card">
                        <b>📍 {row['Место']}</b><br>
                        <b>{row['Наименование товара']}</b><br>
                        <small>Заказ: {row['Номер заказа']} | Кол-во: {row['Кол-во']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"▶️ Взять в работу", key=f"btn_{idx}", use_container_width=True):
                        st.session_state.cell_number = row['Место']
                        task = find_task(st.session_state.tasks_df, row['Место'])
                        if task is not None:
                            stock = find_stock(st.session_state.stock_df, task['Артикул/Код OZON'])
                            if stock is not None:
                                st.session_state.current_task = task
                                st.session_state.current_stock = stock
                                st.session_state.scanned = []
                                st.session_state.imeis = []
                                st.session_state.barcode_scanned = False
                                st.session_state.step = 'scan'
                                st.rerun()
                            else:
                                st.error(f"❌ Товар не найден в остатках")
        else:
            # Все задания выполнены!
            st.markdown("""
            <div style="text-align: center; padding: 40px 20px;">
                <div class="emoji-big">🎉</div>
                <h2 style="color: #4CAF50;">Все задания выполнены!</h2>
                <p style="font-size: 24px;">Отличная работа! 👏</p>
                <p style="font-size: 20px; color: #666;">Вы собрали все заказы</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Показываем отчет
            if st.button("📊 Показать отчет", use_container_width=True):
                st.session_state.step = 'report'
                st.rerun()
    else:
        st.warning("⚠️ Нет заданий")
        if st.button("🔄 Загрузить данные", use_container_width=True):
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
        st.markdown(f'<h2>📍 {task["Место"]}</h2>', unsafe_allow_html=True)
        st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 Товар", task['Наименование товара'][:25] + "...")
        with col2:
            st.metric("📱 Артикул", task['Артикул/Код OZON'])
        
        # Показываем баркод крупно с выделенными последними 4 цифрами
        barcode_full = str(task['Артикул/Код OZON'])
        if len(barcode_full) >= 4:
            barcode_first = barcode_full[:-4]
            barcode_last4 = barcode_full[-4:]
            st.markdown(f"""
            <div class="barcode-label">📷 Сканируйте баркод:</div>
            <div class="barcode-display">
                {barcode_first}<span class="barcode-last4">{barcode_last4}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="barcode-label">📷 Сканируйте баркод:</div>
            <div class="barcode-display">{barcode_full}</div>
            """, unsafe_allow_html=True)
        
        total = int(task['Кол-во'])
        scanned = len(st.session_state.scanned)
        st.progress(scanned / total if total > 0 else 0)
        st.caption(f"📊 Отсканировано: {scanned} из {total}")
        
        if st.session_state.barcode_scanned:
            st.success("✅ Баркод успешно отсканирован!")
        
        barcode = st.text_input("📷 Введите баркод", placeholder="Наведите сканер...", key="barcode_input")
        
        if barcode:
            if barcode.strip() == str(task['Артикул/Код OZON']).strip():
                if not st.session_state.barcode_scanned:
                    st.session_state.scanned.append(barcode)
                    st.session_state.barcode_scanned = True
                    st.success(f"✅ Баркод принят! ({len(st.session_state.scanned)}/{total})")
                    
                    if stock is not None and stock.get('Имеи', '').lower() == 'да':
                        st.session_state.imeis = []
                        st.session_state.step = 'imei'
                        st.rerun()
                    else:
                        if len(st.session_state.scanned) >= total:
                            record = {
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
                                'Имеи1': '',
                                'Имеи2': '',
                                'Время отбора': get_tashkent_time(),
                                'Место': str(st.session_state.cell_number)
                            }
                            if save_to_gsheet(record):
                                st.session_state.completed.append(record)
                                st.session_state.completed_orders.append(str(task['Номер заказа']))
                                st.session_state.step = 'finish'
                                st.rerun()
                            else:
                                st.error("❌ Ошибка сохранения. Попробуйте еще раз.")
                        else:
                            st.rerun()
                else:
                    st.warning("⚠️ Баркод уже отсканирован!")
            else:
                st.error("❌ Неверный баркод!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Назад", use_container_width=True):
                st.session_state.step = 'main'
                st.rerun()
        with col2:
            if scanned >= total and st.session_state.barcode_scanned:
                if st.button("✅ Завершить", use_container_width=True):
                    record = {
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
                        'Имеи1': '',
                        'Имеи2': '',
                        'Время отбора': get_tashkent_time(),
                        'Место': str(st.session_state.cell_number)
                    }
                    if save_to_gsheet(record):
                        st.session_state.completed.append(record)
                        st.session_state.completed_orders.append(str(task['Номер заказа']))
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
    
    if not st.session_state.barcode_scanned:
        st.error("❌ Сначала отсканируйте баркод!")
        if st.button("🔙 Вернуться к сканированию", use_container_width=True):
            st.session_state.step = 'scan'
            st.rerun()
    else:
        current = len(st.session_state.imeis)
        
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
                st.session_state.completed_orders.append(str(task['Номер заказа']))
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
    
    # Интересная анимация вместо шаров
    emojis = ['🎉', '✨', '⭐', '🌟', '💫', '🎊', '🏆', '🥇']
    selected_emojis = random.sample(emojis, 4)
    
    st.markdown(f"""
    <div style="text-align: center; padding: 30px 20px;">
        <div style="font-size: 80px; animation: celebrate 0.5s ease 3;">
            {selected_emojis[0]} {selected_emojis[1]}
            <br>
            {selected_emojis[2]} {selected_emojis[3]}
        </div>
        <h2 style="color: #4CAF50; margin-top: 20px;">✅ Задание выполнено!</h2>
        <div style="font-size: 28px; margin: 10px 0;">
            🎯 {task['Наименование товара']}
        </div>
        <div style="font-size: 24px; color: #666;">
            📦 Заказ: {task['Номер заказа']}
        </div>
        <div style="font-size: 20px; color: #888; margin-top: 10px;">
            🕐 {get_tashkent_time()}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Показываем прогресс
    total_tasks = len(st.session_state.tasks_df) if st.session_state.tasks_df is not None else 0
    done_tasks = len(st.session_state.completed_orders)
    remaining = total_tasks - done_tasks
    
    st.markdown(f"""
    <div style="background: #f8f9fa; border-radius: 15px; padding: 20px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div>
                <div style="font-size: 32px; font-weight: bold; color: #4CAF50;">{done_tasks}</div>
                <div style="font-size: 18px; color: #666;">✅ Выполнено</div>
            </div>
            <div>
                <div style="font-size: 32px; font-weight: bold; color: #FF9800;">{remaining}</div>
                <div style="font-size: 18px; color: #666;">📋 Осталось</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Следующее", use_container_width=True):
            st.session_state.step = 'main'
            st.session_state.current_task = None
            st.session_state.current_stock = None
            st.session_state.scanned = []
            st.session_state.imeis = []
            st.session_state.barcode_scanned = False
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
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Скачать отчет",
            csv,
            f"отчет_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv",
            use_container_width=True
        )
        
        st.caption(f"✅ Всего выполнено: {len(df)} заданий")
    else:
        st.info("📭 Нет выполненных заданий")
    
    if st.button("🔙 На главную", use_container_width=True):
        st.session_state.step = 'main'
        st.rerun()
