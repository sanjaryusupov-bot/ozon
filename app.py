import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import re

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Сборка заказов", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- СКРЫВАЕМ БОКОВУЮ ПАНЕЛЬ ПОЛНОСТЬЮ ---
st.markdown("""
<style>
    /* Скрываем боковую панель */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    /* Убираем отступы для основного контента */
    .main > div {
        padding: 1rem 0.5rem !important;
    }
    /* Крупные элементы для телефона */
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
    }
    h1 { font-size: 36px !important; text-align: center !important; }
    h2 { font-size: 30px !important; text-align: center !important; }
    h3 { font-size: 26px !important; text-align: center !important; }
    p, div, span, label { font-size: 22px !important; }
    /* Метрики */
    [data-testid="metric-container"] {
        background: #f0f2f6;
        border-radius: 15px;
        padding: 15px;
        margin: 5px 0;
        text-align: center;
    }
    /* Прогресс-бар */
    .stProgress > div > div {
        height: 30px !important;
        border-radius: 15px !important;
    }
    /* Карточка задания */
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
        opacity: 0.7;
    }
    /* Время */
    .time-display {
        text-align: center;
        color: #666;
        font-size: 18px !important;
        margin: 5px 0;
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
        return None, None, None
    
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
        
        return tasks_df, stock_df, ref_df
    except Exception as e:
        st.error(f"❌ Ошибка загрузки: {e}")
        return None, None, None

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
        
        # Сохраняем в основную таблицу "Остатки" - обновляем IMEI
        try:
            worksheet_stock = sh.worksheet("Остатки")
            stock_data = worksheet_stock.get_all_values()
            
            # Ищем строку с нужным артикулом и местом
            for i, row in enumerate(stock_data):
                if len(row) >= 3:
                    place = str(row[0]).strip() if len(row) > 0 else ''
                    article = str(row[2]).strip() if len(row) > 2 else ''
                    if place == str(record.get('Место', '')).strip() and article == str(record.get('Артикул/Код OZON', '')).strip():
                        # Обновляем IMEI1 и IMEI2
                        # Индексы: 0-Место, 1-Наименование, 2-Артикул, 3-Кол-во, 4-№ поставки, 5-№ ГТД, 6-Имеи, 7-Длина, 8-Ширина, 9-Высота, 10-вес, 11-Имеи1, 12-Имеи2
                        if len(row) > 11:
                            worksheet_stock.update_cell(i+1, 12, record.get('Имеи1', ''))
                        if len(row) > 12:
                            worksheet_stock.update_cell(i+1, 13, record.get('Имеи2', ''))
                        break
        except Exception as e:
            st.error(f"❌ Ошибка обновления остатков: {e}")
        
        # Сохраняем в лог сканирований
        log_name = "Лог_сканирований"
        try:
            ws = sh.worksheet(log_name)
        except:
            ws = sh.add_worksheet(title=log_name, rows="10000", cols="20")
            headers = ['Номер заказа', 'Наименование товара', 'Артикул/Код OZON', 
                      'Кол-во', '№ поставки', '№ ГТД', 'Имеи', 'Длина', 'Ширина', 
                      'Высота', 'вес', 'Имеи1', 'Имеи2', 'Время отбора', 'Место', 
                      'Баркод', 'IMEI']
            ws.append_row(headers)
        
        row = [
            record.get('Номер заказа', ''),
            record.get('Наименование товара', ''),
            record.get('Артикул/Код OZON', ''),
            record.get('Кол-во', ''),
            record.get('№ поставки', ''),
            record.get('№ ГТД', ''),
            record.get('Имеи', ''),
            record.get('Длина', ''),
            record.get('Ширина', ''),
            record.get('Высота', ''),
            record.get('вес', ''),
            record.get('Имеи1', ''),
            record.get('Имеи2', ''),
            record.get('Время отбора', ''),
            record.get('Место', ''),
            record.get('Баркод', ''),
            record.get('IMEI', '')
        ]
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ Ошибка сохранения: {e}")
        return False

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

# --- ЗАГРУЗКА ДАННЫХ ---
if not st.session_state.data_loaded:
    with st.spinner("Загрузка данных..."):
        tasks, stock, ref = load_all_data()
        if tasks is not None:
            st.session_state.tasks_df = tasks
            st.session_state.stock_df = stock
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
        st.subheader("📋 Задания")
        
        completed_orders = [c.get('Номер заказа') for c in st.session_state.completed]
        
        for idx, row in st.session_state.tasks_df.iterrows():
            is_done = row['Номер заказа'] in completed_orders
            
            with st.container():
                if not is_done:
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
                                st.session_state.step = 'scan'
                                st.rerun()
                            else:
                                st.error(f"❌ Товар не найден в остатках")
                else:
                    st.markdown(f"""
                    <div class="task-card-done">
                        ✅ <b>{row['Наименование товара']}</b><br>
                        <small>Заказ: {row['Номер заказа']} | Готово!</small>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Нет активных заданий")
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
        
        total = int(task['Кол-во'])
        scanned = len(st.session_state.scanned)
        st.progress(scanned / total if total > 0 else 0)
        st.caption(f"📊 Отсканировано: {scanned} из {total}")
        
        barcode = st.text_input("📷 Сканируйте баркод", placeholder="Наведите сканер...", key="barcode_input")
        
        if barcode:
            if barcode.strip() == str(task['Артикул/Код OZON']).strip():
                st.session_state.scanned.append(barcode)
                st.success(f"✅ Баркод принят! ({len(st.session_state.scanned)}/{total})")
                
                # Проверяем IMEI
                if stock is not None and stock.get('Имеи', '').lower() == 'да':
                    st.session_state.imeis = []
                    st.session_state.step = 'imei'
                    st.rerun()
                else:
                    if len(st.session_state.scanned) >= total:
                        # Сохраняем без IMEI
                        record = {
                            'Номер заказа': task['Номер заказа'],
                            'Наименование товара': task['Наименование товара'],
                            'Артикул/Код OZON': task['Артикул/Код OZON'],
                            'Кол-во': task['Кол-во'],
                            '№ поставки': stock.get('№ поставки', '') if stock is not None else '',
                            '№ ГТД': stock.get('№ ГТД', '') if stock is not None else '',
                            'Имеи': stock.get('Имеи', 'Нет') if stock is not None else 'Нет',
                            'Длина': stock.get('Длина', '') if stock is not None else '',
                            'Ширина': stock.get('Ширина', '') if stock is not None else '',
                            'Высота': stock.get('Высота', '') if stock is not None else '',
                            'вес': stock.get('вес', '') if stock is not None else '',
                            'Имеи1': '',
                            'Имеи2': '',
                            'Время отбора': get_tashkent_time(),
                            'Место': st.session_state.cell_number,
                            'Баркод': barcode,
                            'IMEI': ''
                        }
                        save_to_gsheet(record)
                        st.session_state.completed.append(record)
                        st.session_state.step = 'finish'
                        st.rerun()
                    else:
                        st.rerun()
            else:
                st.error("❌ Неверный баркод")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Назад", use_container_width=True):
                st.session_state.step = 'main'
                st.rerun()
        with col2:
            if scanned >= total:
                if st.button("✅ Завершить", use_container_width=True):
                    record = {
                        'Номер заказа': task['Номер заказа'],
                        'Наименование товара': task['Наименование товара'],
                        'Артикул/Код OZON': task['Артикул/Код OZON'],
                        'Кол-во': task['Кол-во'],
                        '№ поставки': stock.get('№ поставки', '') if stock is not None else '',
                        '№ ГТД': stock.get('№ ГТД', '') if stock is not None else '',
                        'Имеи': stock.get('Имеи', 'Нет') if stock is not None else 'Нет',
                        'Длина': stock.get('Длина', '') if stock is not None else '',
                        'Ширина': stock.get('Ширина', '') if stock is not None else '',
                        'Высота': stock.get('Высота', '') if stock is not None else '',
                        'вес': stock.get('вес', '') if stock is not None else '',
                        'Имеи1': '',
                        'Имеи2': '',
                        'Время отбора': get_tashkent_time(),
                        'Место': st.session_state.cell_number,
                        'Баркод': '',
                        'IMEI': ''
                    }
                    save_to_gsheet(record)
                    st.session_state.completed.append(record)
                    st.session_state.step = 'finish'
                    st.rerun()

# --- ВВОД IMEI ---
elif st.session_state.step == 'imei':
    stock = st.session_state.current_stock
    task = st.session_state.current_task
    
    st.subheader(f"📱 Введите IMEI")
    st.write(f"**{task['Наименование товара']}**")
    st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)
    
    # Определяем, сколько IMEI нужно ввести
    # Всегда запрашиваем 2 IMEI, если второй нет - вводим 0
    current = len(st.session_state.imeis)
    
    if current == 0:
        st.write("**Введите IMEI 1**")
        label = "IMEI 1"
        placeholder = "Введите 15 цифр"
        st.info("ℹ️ Введите первый IMEI (15 цифр)")
    elif current == 1:
        st.write("**Введите IMEI 2**")
        label = "IMEI 2"
        placeholder = "Введите 15 цифр или 0"
        st.info("ℹ️ Введите второй IMEI (15 цифр) или 0, если его нет")
    else:
        # Все IMEI введены - сохраняем
        task = st.session_state.current_task
        stock = st.session_state.current_stock
        
        # Проверяем уникальность IMEI
        imei1 = st.session_state.imeis[0] if len(st.session_state.imeis) > 0 else ''
        imei2 = st.session_state.imeis[1] if len(st.session_state.imeis) > 1 else ''
        
        # Если оба IMEI есть и они одинаковые - ошибка
        if imei1 and imei2 and imei1 != '0' and imei2 != '0' and imei1 == imei2:
            st.error("❌ IMEI не могут быть одинаковыми! Вернитесь и введите разные IMEI.")
            if st.button("🔙 Вернуться к вводу IMEI", use_container_width=True):
                st.session_state.imeis = []
                st.rerun()
            return
        
        record = {
            'Номер заказа': task['Номер заказа'],
            'Наименование товара': task['Наименование товара'],
            'Артикул/Код OZON': task['Артикул/Код OZON'],
            'Кол-во': task['Кол-во'],
            '№ поставки': stock.get('№ поставки', '') if stock is not None else '',
            '№ ГТД': stock.get('№ ГТД', '') if stock is not None else '',
            'Имеи': stock.get('Имеи', 'Нет') if stock is not None else 'Нет',
            'Длина': stock.get('Длина', '') if stock is not None else '',
            'Ширина': stock.get('Ширина', '') if stock is not None else '',
            'Высота': stock.get('Высота', '') if stock is not None else '',
            'вес': stock.get('вес', '') if stock is not None else '',
            'Имеи1': imei1,
            'Имеи2': imei2 if imei2 != '0' else '',
            'Время отбора': get_tashkent_time(),
            'Место': st.session_state.cell_number,
            'Баркод': '',
            'IMEI': f"{imei1}, {imei2}" if imei2 and imei2 != '0' else imei1
        }
        
        if save_to_gsheet(record):
            st.success("✅ Данные сохранены в Google Sheets!")
            st.session_state.completed.append(record)
            st.session_state.step = 'finish'
            st.rerun()
        else:
            st.error("❌ Ошибка сохранения. Попробуйте еще раз.")
    
    imei_input = st.text_input(label, placeholder=placeholder, key="imei_input")
    
    if imei_input:
        # Проверка формата
        if imei_input == '0' or re.match(r'^\d{15}$', imei_input):
            # Проверка на дублирование с уже введенным IMEI
            if len(st.session_state.imeis) == 1 and imei_input != '0':
                first_imei = st.session_state.imeis[0]
                if imei_input == first_imei:
                    st.error("❌ IMEI не могут быть одинаковыми! Введите другой IMEI.")
                else:
                    st.session_state.imeis.append(imei_input)
                    st.success(f"✅ IMEI {len(st.session_state.imeis)} сохранен")
                    st.rerun()
            else:
                st.session_state.imeis.append(imei_input)
                st.success(f"✅ IMEI {len(st.session_state.imeis)} сохранен")
                st.rerun()
        else:
            st.error("❌ Введите 15 цифр или 0")
    
    if st.button("🔙 Назад", use_container_width=True):
        st.session_state.step = 'scan'
        st.rerun()

# --- ЗАВЕРШЕНИЕ ---
elif st.session_state.step == 'finish':
    task = st.session_state.current_task
    
    st.balloons()
    st.success("✅ Задание выполнено!")
    
    st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown(f"""
        <div style="background: #f0f8f0; border-radius: 15px; padding: 20px; margin: 10px 0;">
            <b>✅ {task['Наименование товара']}</b><br>
            <small>Заказ: {task['Номер заказа']}</small>
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
