import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Сборка Заказов", layout="centered")

# --- ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ---
def connect_to_gsheet():
    try:
        if "google" not in st.secrets:
            return None
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["google"]["service_account_key"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_id = "109S4MTu32nb2Ou5JiYEmWxj1urNxLXAc0vZjD5JS-F4"
        return client.open_by_key(sheet_id)
    except Exception as e:
        st.sidebar.error(f"Ошибка: {e}")
        return None

# --- ЗАГРУЗКА ДАННЫХ ---
def load_data():
    sh = connect_to_gsheet()
    if sh is None:
        return get_test_data()
    
    try:
        # Загружаем задания
        worksheet_tasks = sh.worksheet("Отбор")
        tasks_data = worksheet_tasks.get_all_values()
        if len(tasks_data) > 1:
            tasks_df = pd.DataFrame(tasks_data[1:], columns=tasks_data[0])
            tasks_df.columns = tasks_df.columns.str.strip()
        else:
            tasks_df = pd.DataFrame(columns=['Номер заказа', 'Артикул/Код OZON', 'Наименование товара', 'Место', 'Кол-во'])
        
        # Загружаем остатки
        worksheet_stock = sh.worksheet("Остатки")
        stock_data = worksheet_stock.get_all_values()
        if len(stock_data) > 1:
            stock_df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
            stock_df.columns = stock_df.columns.str.strip()
            if 'Кол-во' in stock_df.columns:
                stock_df['Кол-во'] = pd.to_numeric(stock_df['Кол-во'], errors='coerce')
        else:
            stock_df = pd.DataFrame(columns=['Место', 'Наименование товара', 'Артикул/Код OZON', 'Кол-во', '№ поставки', '№ ГТД', 'Имеи', 'Длина', 'Ширина', 'Высота', 'вес', 'Имеи1', 'Имеи2'])
        
        return tasks_df, stock_df
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return get_test_data()

# --- ТЕСТОВЫЕ ДАННЫЕ ---
def get_test_data():
    tasks_data = {
        'Номер заказа': ['0153567258-0108-1', '19346551-0329-1', '50156854-0038-1'],
        'Артикул/Код OZON': ['195950627503', '195950543667', '195950643442'],
        'Наименование товара': ['iPhone 17 pro 256GB', 'AirPods pro 3', 'iPhone 17 256GB black'],
        'Место': ['2HM1-1-1-1001', '2HM1-1-1-1004', '2HM1-1-1-2103'],
        'Кол-во': ['1', '1', '1']
    }
    tasks_df = pd.DataFrame(tasks_data)
    
    stock_data = {
        'Место': ['2HM1-1-1-1001', '2HM1-1-1-1004', '2HM1-1-1-2103'],
        'Наименование товара': ['iPhone 17 pro 256GB', 'AirPods pro 3', 'iPhone 17 256GB black'],
        'Артикул/Код OZON': ['195950627503', '195950543667', '195950643442'],
        'Кол-во': ['5', '3', '2'],
        '№ поставки': ['PO-001', 'PO-002', 'PO-003'],
        '№ ГТД': ['GTD-001', 'GTD-002', 'GTD-003'],
        'Имеи': ['Да', 'Нет', 'Да'],
        'Длина': ['15', '5', '15'],
        'Ширина': ['7', '3', '7'],
        'Высота': ['1', '2', '1'],
        'вес': ['0.2', '0.05', '0.2'],
        'Имеи1': ['123456789012345', '', '987654321098765'],
        'Имеи2': ['111222333444555', '', '555444333222111']
    }
    stock_df = pd.DataFrame(stock_data)
    return tasks_df, stock_df

# --- ИНИЦИАЛИЗАЦИЯ ---
if 'step' not in st.session_state:
    st.session_state.step = 'cell'
if 'current_task' not in st.session_state:
    st.session_state.current_task = None
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = None
if 'scanned' not in st.session_state:
    st.session_state.scanned = []
if 'imeis' not in st.session_state:
    st.session_state.imeis = []
if 'cell_number' not in st.session_state:
    st.session_state.cell_number = ""
if 'tasks_df' not in st.session_state:
    st.session_state.tasks_df, st.session_state.stock_df = load_data()
if 'completed' not in st.session_state:
    st.session_state.completed = []
if 'imei_stage' not in st.session_state:
    st.session_state.imei_stage = 0  # 0 - не нужно, 1 - ввод первого, 2 - ввод второго
if 'use_test' not in st.session_state:
    st.session_state.use_test = False

# --- ФУНКЦИИ ---
def find_task(cell):
    try:
        task = st.session_state.tasks_df[st.session_state.tasks_df['Место'].astype(str).str.strip() == str(cell).strip()]
        return task.iloc[0] if not task.empty else None
    except:
        return None

def find_stock(article):
    try:
        items = st.session_state.stock_df[st.session_state.stock_df['Артикул/Код OZON'].astype(str).str.strip() == str(article).strip()]
        return items.iloc[0] if not items.empty else None
    except:
        return None

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки")
    if st.button("🔄 Обновить"):
        st.session_state.tasks_df, st.session_state.stock_df = load_data()
        st.rerun()
    
    test_mode = st.toggle("🧪 Тестовый режим", value=st.session_state.use_test)
    if test_mode != st.session_state.use_test:
        st.session_state.use_test = test_mode
        if test_mode:
            st.session_state.tasks_df, st.session_state.stock_df = get_test_data()
        else:
            st.session_state.tasks_df, st.session_state.stock_df = load_data()
        st.rerun()
    
    st.divider()
    st.caption(f"Заданий: {len(st.session_state.tasks_df) if st.session_state.tasks_df is not None else 0}")
    
    if st.button("🔄 Начать сначала"):
        for key in ['step', 'current_task', 'current_stock', 'scanned', 'imeis', 'cell_number', 'imei_stage']:
            if key in st.session_state:
                if key == 'step':
                    st.session_state[key] = 'cell'
                elif key == 'scanned':
                    st.session_state[key] = []
                elif key == 'imeis':
                    st.session_state[key] = []
                elif key == 'imei_stage':
                    st.session_state[key] = 0
                else:
                    st.session_state[key] = None
        st.rerun()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
st.title("📦 Сборка")

# Статус
if st.session_state.use_test:
    st.info("🧪 Тестовый режим")

# === ШАГ 1: ВВОД ЯЧЕЙКИ ===
if st.session_state.step == 'cell':
    st.subheader("📍 Введите ячейку")
    
    cell = st.text_input("Номер ячейки", placeholder="Напр. 2HM1-1-1-1001", key="cell_input")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("✅ Найти", use_container_width=True):
            if cell:
                task = find_task(cell)
                if task is not None:
                    stock = find_stock(task['Артикул/Код OZON'])
                    if stock is not None:
                        st.session_state.current_task = task
                        st.session_state.current_stock = stock
                        st.session_state.cell_number = cell
                        st.session_state.scanned = []
                        st.session_state.imeis = []
                        st.session_state.imei_stage = 0
                        st.session_state.step = 'scan'
                        st.rerun()
                    else:
                        st.error("❌ Товар не найден в остатках")
                else:
                    st.error("❌ Ячейка не найдена")
            else:
                st.warning("⚠️ Введите номер")

# === ШАГ 2: СКАНИРОВАНИЕ ===
elif st.session_state.step == 'scan':
    task = st.session_state.current_task
    stock = st.session_state.current_stock
    
    if task is None or stock is None:
        st.error("Ошибка данных")
        if st.button("Начать сначала"):
            st.session_state.step = 'cell'
            st.rerun()
    else:
        total = int(task['Кол-во'])
        scanned = len(st.session_state.scanned)
        
        # Информация
        st.subheader(f"📍 {st.session_state.cell_number}")
        st.write(f"**{task['Наименование товара']}**")
        st.write(f"Артикул: `{task['Артикул/Код OZON']}`")
        st.write(f"Остаток: {stock.get('Кол-во', '?')} шт.")
        
        # Прогресс
        st.progress(scanned / total if total > 0 else 0)
        st.caption(f"Отсканировано: {scanned} из {total}")
        
        # Поле для сканирования
        barcode = st.text_input("📷 Сканируйте баркод", placeholder="Наведите сканер...", key="barcode_input")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✅ ОК", use_container_width=True):
                if barcode:
                    if barcode.strip() == str(task['Артикул/Код OZON']).strip():
                        st.session_state.scanned.append(barcode)
                        st.success(f"✅ {len(st.session_state.scanned)}/{total}")
                        
                        # Проверяем IMEI
                        if stock.get('Имеи', 'Нет') == 'Да':
                            st.session_state.imei_stage = 1
                            st.session_state.imeis = []
                            st.session_state.step = 'imei'
                            st.rerun()
                        else:
                            if len(st.session_state.scanned) >= total:
                                st.session_state.step = 'finish'
                                st.rerun()
                            else:
                                st.rerun()
                    else:
                        st.error("❌ Неверный баркод")
                else:
                    st.warning("⚠️ Введите баркод")
        
        # Кнопка пропуска если всё собрано
        if scanned >= total:
            if st.button("✅ Завершить сборку", use_container_width=True):
                st.session_state.step = 'finish'
                st.rerun()

# === ШАГ 3: ВВОД IMEI ===
elif st.session_state.step == 'imei':
    stock = st.session_state.current_stock
    task = st.session_state.current_task
    
    # Определяем сколько IMEI нужно
    has_imei1 = pd.notna(stock.get('Имеи1', '')) and stock.get('Имеи1', '') != ''
    has_imei2 = pd.notna(stock.get('Имеи2', '')) and stock.get('Имеи2', '') != ''
    
    # Если оба есть - вводим 2, иначе 1
    need_imei2 = has_imei1 and has_imei2
    current_imei = len(st.session_state.imeis)
    
    st.subheader(f"📱 IMEI для {task['Наименование товара']}")
    
    # Определяем какое IMEI вводим
    if current_imei == 0:
        st.write("**Введите IMEI 1**")
        label = "IMEI 1"
    elif need_imei2 and current_imei == 1:
        st.write("**Введите IMEI 2**")
        label = "IMEI 2"
    else:
        # Все IMEI введены
        st.session_state.step = 'finish'
        st.rerun()
    
    imei_input = st.text_input(label, placeholder="Введите 15 цифр или 0 если нет", key="imei_input")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("✅ ОК", use_container_width=True):
            if imei_input:
                # Проверяем 0 или 15 цифр
                if imei_input == '0' or re.match(r'^\d{15}$', imei_input):
                    st.session_state.imeis.append(imei_input)
                    st.success(f"✅ IMEI {len(st.session_state.imeis)} сохранен")
                    
                    # Проверяем, нужно ли еще IMEI
                    if need_imei2 and len(st.session_state.imeis) < 2:
                        st.rerun()
                    else:
                        st.session_state.step = 'finish'
                        st.rerun()
                else:
                    st.error("❌ Введите 15 цифр или 0")
            else:
                st.warning("⚠️ Введите IMEI или 0")

# === ШАГ 4: ЗАВЕРШЕНИЕ ===
elif st.session_state.step == 'finish':
    task = st.session_state.current_task
    stock = st.session_state.current_stock
    
    if task is not None:
        st.balloons()
        st.success(f"✅ Готово! {task['Наименование товара']}")
        
        # Сохраняем
        record = {
            'Номер заказа': task['Номер заказа'],
            'Наименование товара': task['Наименование товара'],
            'Артикул/Код OZON': task['Артикул/Код OZON'],
            'Кол-во': task['Кол-во'],
            '№ поставки': stock.get('№ поставки', ''),
            '№ ГТД': stock.get('№ ГТД', ''),
            'Имеи': stock.get('Имеи', 'Нет'),
            'Длина': stock.get('Длина', ''),
            'Ширина': stock.get('Ширина', ''),
            'Высота': stock.get('Высота', ''),
            'вес': stock.get('вес', ''),
            'Имеи1': st.session_state.imeis[0] if len(st.session_state.imeis) > 0 else '',
            'Имеи2': st.session_state.imeis[1] if len(st.session_state.imeis) > 1 else '',
            'Время отбора': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Место': st.session_state.cell_number
        }
        st.session_state.completed.append(record)
        
        # Кнопки
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Следующее", use_container_width=True):
                st.session_state.step = 'cell'
                st.session_state.current_task = None
                st.session_state.current_stock = None
                st.session_state.scanned = []
                st.session_state.imeis = []
                st.session_state.imei_stage = 0
                st.rerun()
        with col2:
            if st.button("📊 Отчет", use_container_width=True):
                st.session_state.step = 'report'
                st.rerun()

# === ШАГ 5: ОТЧЕТ ===
elif st.session_state.step == 'report':
    st.subheader("📊 Отчет")
    
    if st.session_state.completed:
        df = pd.DataFrame(st.session_state.completed)
        st.dataframe(df, use_container_width=True)
        
        # Скачать
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Скачать CSV", csv, f"отчет_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        
        # Сохранить в Google Sheets
        if not st.session_state.use_test:
            if st.button("💾 Сохранить в Google Sheets"):
                sh = connect_to_gsheet()
                if sh:
                    try:
                        name = f"Отчет_{datetime.now().strftime('%Y-%m-%d')}"
                        try:
                            ws = sh.add_worksheet(title=name, rows="1000", cols="20")
                        except:
                            sh.del_worksheet(sh.worksheet(name))
                            ws = sh.add_worksheet(title=name, rows="1000", cols="20")
                        ws.append_row(list(df.columns))
                        for _, row in df.iterrows():
                            ws.append_row(row.astype(str).tolist())
                        st.success("✅ Сохранено!")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
    else:
        st.info("Нет выполненных заданий")
    
    if st.button("🔄 Новая смена", use_container_width=True):
        st.session_state.step = 'cell'
        st.session_state.completed = []
        st.rerun()

# --- СТИЛИ ДЛЯ ТЕЛЕФОНА ---
st.markdown("""
<style>
    /* Крупные элементы для телефона */
    .stTextInput input {
        font-size: 24px !important;
        padding: 20px !important;
        height: 70px !important;
    }
    .stButton button {
        font-size: 24px !important;
        padding: 15px !important;
        height: 60px !important;
        width: 100% !important;
    }
    /* Метрики */
    [data-testid="metric-container"] {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
    /* Заголовки */
    h1, h2, h3 {
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)
