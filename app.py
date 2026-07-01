import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
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
    /* Успешное сканирование */
    .scan-success {
        background: #d4edda;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    .scan-error {
        background: #f8d7da;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    /* Время */
    .time-display {
        text-align: center;
        color: #666;
        font-size: 18px !important;
        margin: 5px 0;
    }
    /* Кнопка "Назад" делаем меньше */
    .back-button button {
        font-size: 20px !important;
        height: 50px !important;
        background: #6c757d !important;
    }
    /* Контейнер для кнопок */
    .button-container {
        display: flex;
        gap: 10px;
        margin: 10px 0;
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

# --- ФУНКЦИЯ СОХРАНЕНИЯ В GOOGLE SHEETS (АВТОСОХРАНЕНИЕ) ---
def save_to_gsheet(record):
    """Автоматически сохраняет каждое сканирование в Google Sheets"""
    try:
        sh = connect_to_gsheet()
        if sh is None:
            return False
        
        # Создаем или получаем вкладку для лога сканирований
        log_name = "Лог_сканирований"
        try:
            ws = sh.worksheet(log_name)
        except:
            ws = sh.add_worksheet(title=log_name, rows="10000", cols="20")
            # Заголовки
            headers = ['Номер заказа', 'Наименование товара', 'Артикул/Код OZON', 
                      'Кол-во', '№ поставки', '№ ГТД', 'Имеи', 'Длина', 'Ширина', 
                      'Высота', 'вес', 'Имеи1', 'Имеи2', 'Время отбора', 'Место', 
                      'Баркод', 'IMEI']
            ws.append_row(headers)
        
        # Формируем строку
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

# --- ПОЛУЧЕНИЕ ТАШКЕНТСКОГО ВРЕМЕНИ ---
def get_tashkent_time():
    tz = pytz.timezone('Asia/Tashkent')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

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
if 'saved_orders' not in st.session_state:
    st.session_state.saved_orders = []  # Для отслеживания сохраненных заказов

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
    
    # Индикатор времени
    st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)
    
    # Кнопка обновления
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄", use_container_width=True):
            st.session_state.data_loaded = False
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    if st.session_state.tasks_df is not None and not st.session_state.tasks_df.empty:
        st.subheader("📋 Задания")
        
        # Фильтруем уже выполненные заказы
        completed_orders = [c.get('Номер заказа') for c in st.session_state.completed]
        
        for idx, row in st.session_state.tasks_df.iterrows():
            is_done = row['Номер заказа'] in completed_orders
            
            with st.container():
                if not is_done:
                    st.markdown(f"""
                    <div class="task-card">
                        <b>📍 {row['Место']}</b><br>
                        <b>{row['Наименование товара']}</b><br>
                        <small>Заказ: {row['Номер заказа']}</small>
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
        # Заголовок
        st.markdown(f'<h2>📍 {task["Место"]}</h2>', unsafe_allow_html=True)
        st.markdown(f'<div class="time-display">🕐 {get_tashkent_time()}</div>', unsafe_allow_html=True)
        
        # Информация о товаре
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 Товар", task['Наименование товара'][:25] + "...")
        with col2:
            st.metric("📱 Артикул", task['Артикул/Код OZON'])
        
        # Прогресс
        total = int(task['Кол-во'])
        scanned = len(st.session_state.scanned)
        st.progress(scanned / total if total > 0 else 0)
        st.caption(f"📊 Отсканировано: {scanned} из {total}")
        
        # Поле для сканирования
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
                        # Автосохранение
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
        
        # Кнопки
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
    
    # Определяем сколько IMEI нужно ввести (всегда 2, если есть)
    current = len(st.session_state.imeis)
    
    if current == 0:
        st.write("**Введите IMEI 1**")
        label = "IMEI 1"
        placeholder = "Введите 15 цифр"
    elif current == 1:
        st.write("**Введите IMEI 2 (или 0, если нет)**")
        label = "IMEI 2"
        placeholder = "15 цифр или 0"
    else:
        # Все IMEI введены - сохраняем
        task = st.session_state.current_task
        stock = st.session_state.current_stock
        
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
            'Имеи1': st.session_state.imeis[0] if len(st.session_state.imeis) > 0 else '',
            'Имеи2': st.session_state.imeis[1] if len(st.session_state.imeis) > 1 else '',
            'Время отбора': get_tashkent_time(),
            'Место': st.session_state.cell_number,
            'Баркод': '',
            'IMEI': ', '.join(st.session_state.imeis)
        }
        save_to_gsheet(record)
        st.session_state.completed.append(record)
        st.session_state.step = 'finish'
        st.rerun()
    
    imei_input = st.text_input(label, placeholder=placeholder, key="imei_input")
    
    if imei_input:
        if imei_input == '0' or re.match(r'^\d{15}$', imei_input):
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
    
    # Кнопки
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
        
        # Скачать CSV
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
