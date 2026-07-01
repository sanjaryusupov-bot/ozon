import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import json

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Сборка заказов", layout="centered")

# --- ФУНКЦИЯ ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS (УЛУЧШЕННАЯ) ---
def connect_to_gsheet():
    """Подключение к Google Sheets с обработкой разных форматов секретов."""
    try:
        # Проверяем наличие секретов
        if "google" not in st.secrets:
            st.sidebar.error("❌ Секрет 'google' не найден. Проверьте настройки.")
            st.sidebar.info("Доступные ключи: " + ", ".join(st.secrets.keys()))
            return None

        google_secret = st.secrets["google"]
        
        # Пытаемся получить ключ в разных форматах
        creds_dict = None
        
        # Вариант 1: если секрет это уже словарь
        if isinstance(google_secret, dict):
            # Проверяем, может быть это уже готовый JSON
            if "type" in google_secret and "project_id" in google_secret:
                creds_dict = google_secret
            else:
                # Может быть ключ вложен в поле "service_account_key"
                if "service_account_key" in google_secret:
                    key_data = google_secret["service_account_key"]
                    if isinstance(key_data, str):
                        try:
                            creds_dict = json.loads(key_data)
                        except:
                            creds_dict = key_data
                    else:
                        creds_dict = key_data
                # Или в поле "credentials"
                elif "credentials" in google_secret:
                    creds_dict = google_secret["credentials"]
                # Или просто берем как есть
                else:
                    creds_dict = google_secret
        
        # Вариант 2: если секрет это строка
        elif isinstance(google_secret, str):
            try:
                creds_dict = json.loads(google_secret)
            except:
                # Может это просто строка с JSON
                st.sidebar.error("❌ Не удалось распарсить JSON")
                return None
        
        if creds_dict is None:
            st.sidebar.error("❌ Не удалось найти данные для подключения")
            return None

        # Проверяем структуру ключа
        if not isinstance(creds_dict, dict):
            st.sidebar.error("❌ Данные не являются словарем")
            return None
            
        if "private_key" not in creds_dict or "client_email" not in creds_dict:
            st.sidebar.error("❌ Отсутствуют обязательные поля в ключе")
            st.sidebar.info(f"Доступные поля: {', '.join(creds_dict.keys())}")
            return None

        # Подключаемся
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # ID вашей таблицы
        sheet_id = "109S4MTu32nb2Ou5JiYEmWxj1urNxLXAc0vZjD5JS-F4"
        return client.open_by_key(sheet_id)
        
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка подключения: {e}")
        return None

# --- ОСТАЛЬНЫЕ ФУНКЦИИ ---
@st.cache_data(ttl=60)
def load_all_data():
    """Загружает и объединяет данные из всех вкладок."""
    sh = connect_to_gsheet()
    if sh is None:
        return None, None, None

    try:
        # 1. Загружаем задания из "Отбор"
        worksheet_tasks = sh.worksheet("Отбор")
        tasks_data = worksheet_tasks.get_all_values()
        if len(tasks_data) > 1:
            tasks_df = pd.DataFrame(tasks_data[1:], columns=tasks_data[0])
            tasks_df.columns = tasks_df.columns.str.strip()
            tasks_df['Кол-во'] = pd.to_numeric(tasks_df['Кол-во'], errors='coerce').fillna(1).astype(int)
            tasks_df['Артикул/Код OZON'] = tasks_df['Артикул/Код OZON'].astype(str).str.replace('.0', '', regex=False).str.strip()
        else:
            tasks_df = pd.DataFrame(columns=['Номер заказа', 'Артикул/Код OZON', 'Наименование товара', 'Место', 'Кол-во'])

        # 2. Загружаем остатки из "Остатки"
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

        # 3. Загружаем справочник из "Справочник"
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
        st.sidebar.error(f"❌ Ошибка загрузки: {e}")
        return None, None, None

def enrich_stock_with_ref(stock_df, ref_df):
    """Добавляет в остатки данные из справочника."""
    if stock_df is None or ref_df is None:
        return stock_df

    enriched_df = stock_df.copy()

    for idx, row in enriched_df.iterrows():
        article = row.get('Артикул/Код OZON', '')
        if not article:
            continue

        ref_row = ref_df[ref_df['Артикул/Код OZON'] == article]
        if ref_row.empty:
            continue

        for col in ['Длина', 'Ширина', 'Высота', 'вес']:
            if col in enriched_df.columns and (pd.isna(row.get(col)) or row.get(col) == ''):
                enriched_df.at[idx, col] = ref_row.iloc[0].get(col, '')

    return enriched_df

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
if 'ref_df' not in st.session_state:
    st.session_state.ref_df = None
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
            st.session_state.stock_df = enrich_stock_with_ref(stock, ref)
            st.session_state.ref_df = ref
            st.session_state.data_loaded = True
        else:
            st.error("❌ Не удалось загрузить данные. Проверьте секреты.")

# --- СТИЛИ ---
st.markdown("""
<style>
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
    }
    h1 { font-size: 40px !important; text-align: center !important; }
    h2 { font-size: 32px !important; text-align: center !important; }
    h3 { font-size: 28px !important; text-align: center !important; }
    p, div, span, label { font-size: 22px !important; }
    [data-testid="metric-container"] {
        background: #f0f2f6;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        text-align: center;
    }
    .stProgress > div > div { height: 30px !important; }
    .task-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Меню")
    
    # Показываем статус секретов для отладки
    with st.expander("🔍 Статус секретов"):
        if "google" in st.secrets:
            st.success("✅ Секрет 'google' найден")
            google_secret = st.secrets["google"]
            st.write(f"Тип: {type(google_secret)}")
            if isinstance(google_secret, dict):
                st.write(f"Ключи: {', '.join(google_secret.keys())}")
                # Проверяем наличие обязательных полей
                if "private_key" in google_secret:
                    st.success("✅ Найден private_key")
                if "client_email" in google_secret:
                    st.success("✅ Найден client_email")
        else:
            st.error("❌ Секрет 'google' не найден")
            st.write("Доступные секреты:", list(st.secrets.keys()))

    if st.button("📋 Задания", use_container_width=True):
        st.session_state.step = 'main'
        st.rerun()

    if st.button("📊 Отчет", use_container_width=True):
        st.session_state.step = 'report'
        st.rerun()

    st.divider()

    tasks_count = len(st.session_state.tasks_df) if st.session_state.tasks_df is not None else 0
    done_count = len(st.session_state.completed)
    st.metric("📦 Заданий", f"{done_count}/{tasks_count}")

    if st.button("🔄 Обновить", use_container_width=True):
        st.session_state.data_loaded = False
        st.cache_data.clear()
        st.rerun()

# --- ОСНОВНОЙ КОД (без изменений) ---
# ... (продолжение кода с main, scan, imei, finish, report)
# Я опустил остальную часть для краткости, но она должна быть полностью скопирована из предыдущего ответа
