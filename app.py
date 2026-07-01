import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Сборка заказов", layout="centered")

# --- ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ---
def connect_to_gsheet():
    """Подключение к Google Sheets через сервисный аккаунт."""
    try:
        # Проверяем наличие секретов
        if "google" not in st.secrets:
            st.sidebar.error("❌ Секреты Google не найдены. Добавьте их в .streamlit/secrets.toml")
            return None

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["google"]["service_account_key"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # ID вашей таблицы
        sheet_id = "109S4MTu32nb2Ou5JiYEmWxj1urNxLXAc0vZjD5JS-F4"
        return client.open_by_key(sheet_id)
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка подключения: {e}")
        return None

# --- ЗАГРУЗКА И ОБРАБОТКА ДАННЫХ ---
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
            # Приводим типы
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
            # Приводим числовые колонки
            for col in ['Длина', 'Ширина', 'Высота', 'вес']:
                if col in ref_df.columns:
                    ref_df[col] = pd.to_numeric(ref_df[col], errors='coerce')
        else:
            ref_df = pd.DataFrame(columns=['Наименования', 'Артикул/Код OZON', 'Цена', 'Длина', 'Ширина', 'Высота', 'вес'])

        return tasks_df, stock_df, ref_df

    except Exception as e:
        st.sidebar.error(f"❌ Ошибка загрузки: {e}")
        return None, None, None

# --- ФУНКЦИЯ ОБЪЕДИНЕНИЯ ДАННЫХ ---
def enrich_stock_with_ref(stock_df, ref_df):
    """Добавляет в остатки данные из справочника, если они пустые."""
    if stock_df is None or ref_df is None:
        return stock_df

    # Создаем копию, чтобы не менять оригинал
    enriched_df = stock_df.copy()

    # Для каждой строки в остатках
    for idx, row in enriched_df.iterrows():
        article = row.get('Артикул/Код OZON', '')
        if not article:
            continue

        # Ищем в справочнике
        ref_row = ref_df[ref_df['Артикул/Код OZON'] == article]
        if ref_row.empty:
            continue

        # Заполняем пустые поля
        for col in ['Длина', 'Ширина', 'Высота', 'вес']:
            if col in enriched_df.columns and (pd.isna(row.get(col)) or row.get(col) == ''):
                enriched_df.at[idx, col] = ref_row.iloc[0].get(col, '')

    return enriched_df

# --- ФУНКЦИИ ПОИСКА ---
def find_task(tasks_df, cell):
    """Находит задание по ячейке."""
    try:
        if tasks_df is None or tasks_df.empty:
            return None
        task = tasks_df[tasks_df['Место'].astype(str).str.strip() == str(cell).strip()]
        return task.iloc[0] if not task.empty else None
    except:
        return None

def find_stock(stock_df, article):
    """Находит товар в остатках по артикулу."""
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

# --- ЗАГРУЗКА ДАННЫХ ПРИ СТАРТЕ ---
if not st.session_state.data_loaded:
    with st.spinner("Загрузка данных из Google Sheets..."):
        tasks, stock, ref = load_all_data()
        if tasks is not None:
            st.session_state.tasks_df = tasks
            st.session_state.stock_df = enrich_stock_with_ref(stock, ref)
            st.session_state.ref_df = ref
            st.session_state.data_loaded = True
        else:
            st.error("Не удалось загрузить данные. Проверьте подключение.")

# --- СТИЛИ ДЛЯ ТЕЛЕФОНА ---
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

    if st.button("📋 Задания", use_container_width=True):
        st.session_state.step = 'main'
        st.rerun()

    if st.button("📊 Отчет", use_container_width=True):
        st.session_state.step = 'report'
        st.rerun()

    st.divider()

    # Статистика
    tasks_count = len(st.session_state.tasks_df) if st.session_state.tasks_df is not None else 0
    done_count = len(st.session_state.completed)
    st.metric("📦 Заданий", f"{done_count}/{tasks_count}")

    if st.button("🔄 Обновить данные", use_container_width=True):
        st.session_state.data_loaded = False
        st.cache_data.clear()
        st.rerun()

    if st.button("🔄 Сбросить сессию", use_container_width=True):
        for key in ['step', 'current_task', 'current_stock', 'scanned', 'imeis', 'cell_number']:
            if key in st.session_state:
                if key == 'step':
                    st.session_state[key] = 'main'
                elif key == 'scanned':
                    st.session_state[key] = []
                elif key == 'imeis':
                    st.session_state[key] = []
                else:
                    st.session_state[key] = None
        st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state.step == 'main':
    st.title("📦 Сборка")

    if st.session_state.tasks_df is not None and not st.session_state.tasks_df.empty:
        st.subheader("📋 Активные задания")

        for idx, row in st.session_state.tasks_df.iterrows():
            # Проверяем, выполнено ли
            is_done = any(c.get('Номер заказа') == row['Номер заказа'] for c in st.session_state.completed)

            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                    <div class="task-card">
                        <b>📍 {row['Место']}</b><br>
                        {row['Наименование товара']}<br>
                        <small>Заказ: {row['Номер заказа']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if not is_done:
                        if st.button(f"▶️", key=f"btn_{idx}", use_container_width=True):
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
                                    st.error(f"❌ Товар с артикулом {task['Артикул/Код OZON']} не найден в остатках")
                    else:
                        st.success("✅")
    else:
        st.warning("⚠️ Нет активных заданий")
        if st.button("🔄 Загрузить данные"):
            st.session_state.data_loaded = False
            st.cache_data.clear()
            st.rerun()

# --- СКАНИРОВАНИЕ ---
elif st.session_state.step == 'scan':
    task = st.session_state.current_task
    stock = st.session_state.current_stock

    if task is None:
        st.error("Ошибка: задание не найдено")
        if st.button("Назад"):
            st.session_state.step = 'main'
            st.rerun()
    else:
        st.subheader(f"📍 {task['Место']}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦", task['Наименование товара'][:20] + "...")
        with col2:
            st.metric("📱", task['Артикул/Код OZON'])

        # Прогресс
        total = int(task['Кол-во'])
        scanned = len(st.session_state.scanned)
        st.progress(scanned / total if total > 0 else 0)
        st.caption(f"Отсканировано: {scanned} из {total}")

        # Поле для сканирования
        barcode = st.text_input("📷 Баркод", placeholder="Сканируйте...", key="barcode_input")

        if barcode:
            if barcode.strip() == str(task['Артикул/Код OZON']).strip():
                st.session_state.scanned.append(barcode)
                st.success(f"✅ {len(st.session_state.scanned)}/{total}")

                # Проверяем IMEI
                if stock is not None and stock.get('Имеи', '').lower() == 'да':
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

        # Кнопка завершения
        if scanned >= total:
            if st.button("✅ Завершить", use_container_width=True):
                st.session_state.step = 'finish'
                st.rerun()

        if st.button("🔙 Назад", use_container_width=True):
            st.session_state.step = 'main'
            st.rerun()

# --- ВВОД IMEI ---
elif st.session_state.step == 'imei':
    stock = st.session_state.current_stock
    task = st.session_state.current_task

    st.subheader(f"📱 IMEI")
    st.write(f"**{task['Наименование товара']}**")

    # Определяем сколько IMEI нужно ввести
    has_imei1 = pd.notna(stock.get('Имеи1', '')) and str(stock.get('Имеи1', '')).strip() != ''
    has_imei2 = pd.notna(stock.get('Имеи2', '')) and str(stock.get('Имеи2', '')).strip() != ''

    current = len(st.session_state.imeis)

    if current == 0:
        st.write("**Введите IMEI 1**")
        label = "IMEI 1"
        placeholder = "15 цифр"
    elif has_imei2 and current == 1:
        st.write("**Введите IMEI 2 (или 0, если нет)**")
        label = "IMEI 2"
        placeholder = "15 цифр или 0"
    else:
        st.session_state.step = 'finish'
        st.rerun()

    imei_input = st.text_input(label, placeholder=placeholder, key="imei_input")

    if imei_input:
        if imei_input == '0' or re.match(r'^\d{15}$', imei_input):
            st.session_state.imeis.append(imei_input)
            st.success(f"✅ IMEI {len(st.session_state.imeis)} сохранен")

            # Проверяем, нужно ли еще IMEI
            if has_imei2 and len(st.session_state.imeis) < 2:
                st.rerun()
            else:
                st.session_state.step = 'finish'
                st.rerun()
        else:
            st.error("❌ Введите 15 цифр или 0")

    if st.button("🔙 Назад"):
        st.session_state.step = 'scan'
        st.rerun()

# --- ЗАВЕРШЕНИЕ ---
elif st.session_state.step == 'finish':
    task = st.session_state.current_task
    stock = st.session_state.current_stock

    st.balloons()
    st.success("✅ Готово!")

    # Формируем запись
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
        'Время отбора': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Место': st.session_state.cell_number
    }
    st.session_state.completed.append(record)

    # Кнопки
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 К списку", use_container_width=True):
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

    if st.session_state.completed:
        df = pd.DataFrame(st.session_state.completed)
        st.dataframe(df, use_container_width=True)

        # Скачать CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Скачать CSV",
            csv,
            f"отчет_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv"
        )

        # Сохранить в Google Sheets
        if st.button("💾 Сохранить в Google Sheets", use_container_width=True):
            sh = connect_to_gsheet()
            if sh:
                try:
                    report_name = f"Отчет_{datetime.now().strftime('%Y-%m-%d')}"
                    # Удаляем старую вкладку, если есть
                    try:
                        old_ws = sh.worksheet(report_name)
                        sh.del_worksheet(old_ws)
                    except:
                        pass
                    # Создаем новую
                    ws = sh.add_worksheet(title=report_name, rows="1000", cols="20")
                    # Записываем заголовки
                    ws.append_row(list(df.columns))
                    # Записываем данные
                    for _, row in df.iterrows():
                        ws.append_row(row.astype(str).tolist())
                    st.success(f"✅ Отчет сохранен в вкладку '{report_name}'!")
                except Exception as e:
                    st.error(f"❌ Ошибка сохранения: {e}")
            else:
                st.error("❌ Нет подключения к Google Sheets")

        st.caption(f"Всего выполнено: {len(df)} заданий")
    else:
        st.info("Нет выполненных заданий")

    if st.button("🔙 На главную", use_container_width=True):
        st.session_state.step = 'main'
        st.rerun()
