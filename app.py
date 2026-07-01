import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Система Сборки Заказов", layout="wide")

# --- ФУНКЦИЯ ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS ---
def connect_to_gsheet():
    """Подключение к Google Sheets с использованием сервисного аккаунта."""
    try:
        # Проверяем наличие секретов
        if "google" not in st.secrets:
            st.sidebar.warning("⚠️ Секреты Google не найдены. Используйте тестовые данные.")
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

# --- ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ С ДИАГНОСТИКОЙ ---
def load_data(use_test_data=False):
    """Загружает данные из Google Sheets или использует тестовые данные."""
    
    # Если выбраны тестовые данные или нет подключения
    if use_test_data:
        st.sidebar.info("📊 Используются ТЕСТОВЫЕ данные")
        return get_test_data()
    
    sh = connect_to_gsheet()
    if sh is None:
        st.sidebar.warning("⚠️ Нет подключения к Google Sheets. Используем тестовые данные.")
        return get_test_data()

    try:
        # Показываем все доступные вкладки для диагностики
        all_sheets = sh.worksheets()
        sheet_names = [sheet.title for sheet in all_sheets]
        st.sidebar.write("📋 Доступные вкладки:", sheet_names)
        
        # Загружаем задания из вкладки "Отбор"
        try:
            worksheet_tasks = sh.worksheet("Отбор")
            tasks_data = worksheet_tasks.get_all_values()
            st.sidebar.write(f"📊 Вкладка 'Отбор': {len(tasks_data)} строк")
            
            if len(tasks_data) > 1:
                tasks_df = pd.DataFrame(tasks_data[1:], columns=tasks_data[0])
                # Очищаем пробелы в названиях колонок
                tasks_df.columns = tasks_df.columns.str.strip()
                st.sidebar.write("✅ Задания загружены:", len(tasks_df), "шт.")
            else:
                tasks_df = pd.DataFrame(columns=['Номер заказа', 'Артикул/Код OZON', 'Наименование товара', 'Место', 'Кол-во'])
                st.sidebar.warning("⚠️ Вкладка 'Отбор' пуста")
        except Exception as e:
            st.sidebar.error(f"❌ Ошибка загрузки 'Отбор': {e}")
            tasks_df = pd.DataFrame(columns=['Номер заказа', 'Артикул/Код OZON', 'Наименование товара', 'Место', 'Кол-во'])

        # Загружаем остатки из вкладки "Остатки"
        try:
            worksheet_stock = sh.worksheet("Остатки")
            stock_data = worksheet_stock.get_all_values()
            st.sidebar.write(f"📊 Вкладка 'Остатки': {len(stock_data)} строк")
            
            if len(stock_data) > 1:
                stock_df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
                # Очищаем пробелы в названиях колонок
                stock_df.columns = stock_df.columns.str.strip()
                # Приводим кол-во к числу
                if 'Кол-во' in stock_df.columns:
                    stock_df['Кол-во'] = pd.to_numeric(stock_df['Кол-во'], errors='coerce')
                st.sidebar.write("✅ Остатки загружены:", len(stock_df), "шт.")
            else:
                stock_df = pd.DataFrame(columns=['Место', 'Наименование товара', 'Артикул/Код OZON', 'Кол-во', '№ поставки', '№ ГТД', 'Имеи', 'Длина', 'Ширина', 'Высота', 'вес', 'Имеи1', 'Имеи2'])
                st.sidebar.warning("⚠️ Вкладка 'Остатки' пуста")
        except Exception as e:
            st.sidebar.error(f"❌ Ошибка загрузки 'Остатки': {e}")
            stock_df = pd.DataFrame(columns=['Место', 'Наименование товара', 'Артикул/Код OZON', 'Кол-во', '№ поставки', '№ ГТД', 'Имеи', 'Длина', 'Ширина', 'Высота', 'вес', 'Имеи1', 'Имеи2'])

        return tasks_df, stock_df
    except Exception as e:
        st.sidebar.error(f"❌ Общая ошибка: {e}")
        return get_test_data()

# --- ТЕСТОВЫЕ ДАННЫЕ ---
def get_test_data():
    """Возвращает тестовые данные для проверки работы приложения."""
    # Тестовые данные для вкладки "Отбор"
    tasks_data = {
        'Номер заказа': ['0153567258-0108-1', '19346551-0329-1', '50156854-0038-1'],
        'Артикул/Код OZON': ['195950627503', '195950543667', '195950643442'],
        'Наименование товара': ['iPhone 17 pro 256GB', 'AirPods pro 3', 'iPhone 17 256GB black'],
        'Место': ['2HM1-1-1-1001', '2HM1-1-1-1004', '2HM1-1-1-2103'],
        'Кол-во': [1, 1, 1]
    }
    tasks_df = pd.DataFrame(tasks_data)
    
    # Тестовые данные для вкладки "Остатки"
    stock_data = {
        'Место': ['2HM1-1-1-1001', '2HM1-1-1-1004', '2HM1-1-1-2103', '2HM1-1-1-2104'],
        'Наименование товара': ['iPhone 17 pro 256GB', 'AirPods pro 3', 'iPhone 17 256GB black', 'iPhone 17 pro max 256GB'],
        'Артикул/Код OZON': ['195950627503', '195950543667', '195950643442', '195950639155'],
        'Кол-во': [5, 3, 2, 4],
        '№ поставки': ['PO-001', 'PO-002', 'PO-003', 'PO-004'],
        '№ ГТД': ['GTD-001', 'GTD-002', 'GTD-003', 'GTD-004'],
        'Имеи': ['Да', 'Нет', 'Да', 'Нет'],
        'Длина': ['15', '5', '15', '16'],
        'Ширина': ['7', '3', '7', '8'],
        'Высота': ['1', '2', '1', '1'],
        'вес': ['0.2', '0.05', '0.2', '0.25'],
        'Имеи1': ['123456789012345', '', '987654321098765', ''],
        'Имеи2': ['', '', '111222333444555', '']
    }
    stock_df = pd.DataFrame(stock_data)
    
    return tasks_df, stock_df

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---
def find_task_by_cell(tasks_df, cell_number):
    """Находит задание по номеру ячейки (поле 'Место')."""
    try:
        # Ищем задание, где кол-во > 0 или статус не завершен
        task = tasks_df[tasks_df['Место'].astype(str).str.strip() == str(cell_number).strip()]
        if not task.empty:
            return task.iloc[0]
        else:
            return None
    except Exception:
        return None

def find_stock_items(stock_df, article):
    """Находит товары в остатках по артикулу."""
    try:
        items = stock_df[stock_df['Артикул/Код OZON'].astype(str).str.strip() == str(article).strip()]
        return items
    except Exception:
        return pd.DataFrame()

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ СЕССИИ ---
if 'step' not in st.session_state:
    st.session_state.step = 'input_cell'
if 'current_task' not in st.session_state:
    st.session_state.current_task = None
if 'current_stock_item' not in st.session_state:
    st.session_state.current_stock_item = None
if 'scanned_barcodes' not in st.session_state:
    st.session_state.scanned_barcodes = []
if 'entered_imeis' not in st.session_state:
    st.session_state.entered_imeis = []
if 'cell_number' not in st.session_state:
    st.session_state.cell_number = ""
if 'tasks_df' not in st.session_state:
    st.session_state.tasks_df, st.session_state.stock_df = load_data(use_test_data=False)
if 'completed_tasks' not in st.session_state:
    st.session_state.completed_tasks = []
if 'task_start_time' not in st.session_state:
    st.session_state.task_start_time = None
if 'use_test_data' not in st.session_state:
    st.session_state.use_test_data = False

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Переключатель тестовых данных
    test_data_toggle = st.toggle("🧪 Использовать тестовые данные", value=st.session_state.use_test_data)
    if test_data_toggle != st.session_state.use_test_data:
        st.session_state.use_test_data = test_data_toggle
        st.session_state.tasks_df, st.session_state.stock_df = load_data(use_test_data=test_data_toggle)
        st.rerun()
    
    if st.button("🔄 Обновить данные", use_container_width=True):
        st.session_state.tasks_df, st.session_state.stock_df = load_data(use_test_data=st.session_state.use_test_data)
        st.rerun()
    
    st.divider()
    st.header("📖 Инструкция")
    st.markdown("""
    1. **Введите номер ячейки** из задания.
    2. **Сканируйте баркод** товара. При совпадении с артикулом он будет принят.
    3. Если у товара есть IMEI, система попросит ввести его.
    4. После сканирования всех товаров задание завершится.
    5. **Отчет** сохраняется в Google Sheets.
    
    **Цветовая индикация:**
    - ✅ Зеленый - успешно
    - ❌ Красный - ошибка
    - ⚠️ Желтый - предупреждение
    """)
    
    if st.button("🗑️ Сбросить сессию", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key not in ['use_test_data']:
                del st.session_state[key]
        st.rerun()

# --- ЗАГОЛОВОК ---
st.title("📦 Система Сборки Заказов")

# Показываем статус данных
if st.session_state.use_test_data:
    st.info("🧪 Используются ТЕСТОВЫЕ данные. Для работы с реальной таблицей отключите тестовый режим.")
elif st.session_state.tasks_df is not None and not st.session_state.tasks_df.empty:
    st.success(f"✅ Загружено {len(st.session_state.tasks_df)} заданий и {len(st.session_state.stock_df)} позиций остатков")
else:
    st.warning("⚠️ Данные не загружены. Проверьте подключение к Google Sheets или включите тестовый режим.")

# --- ОТОБРАЖЕНИЕ СПИСКА ЗАДАНИЙ ---
with st.expander("📋 Список заданий на сборку"):
    if st.session_state.tasks_df is not None and not st.session_state.tasks_df.empty:
        # Показываем только активные задания (для простоты - все)
        display_df = st.session_state.tasks_df[['Номер заказа', 'Наименование товара', 'Место', 'Кол-во']].copy()
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption(f"Всего заданий: {len(display_df)}")
    else:
        st.info("📭 Нет активных заданий.")

st.divider()

# --- ОСНОВНОЙ РАБОЧИЙ ПРОЦЕСС ---

# Этап 1: Ввод номера ячейки
if st.session_state.step == 'input_cell':
    st.subheader("🔍 Шаг 1: Введите номер ячейки для отбора")
    
    col_input, col_button = st.columns([3, 1])
    with col_input:
        cell_input = st.text_input("Номер ячейки (например, 2HM1-1-1-1001)", 
                                  placeholder="Введите номер...",
                                  key="cell_input")
    with col_button:
        if st.button("Начать сборку", use_container_width=True):
            if cell_input:
                # Проверяем, есть ли задания
                if st.session_state.tasks_df is None or st.session_state.tasks_df.empty:
                    st.error("❌ Нет загруженных заданий! Проверьте данные.")
                else:
                    # Ищем задание
                    task = find_task_by_cell(st.session_state.tasks_df, cell_input)
                    if task is not None:
                        # Проверяем, есть ли товар в остатках
                        stock_items = find_stock_items(st.session_state.stock_df, task['Артикул/Код OZON'])
                        if not stock_items.empty:
                            # Берем первый подходящий товар
                            stock_item = stock_items.iloc[0]
                            st.session_state.current_task = task
                            st.session_state.current_stock_item = stock_item
                            st.session_state.cell_number = cell_input
                            st.session_state.scanned_barcodes = []
                            st.session_state.entered_imeis = []
                            st.session_state.task_start_time = datetime.now()
                            st.session_state.step = 'scan_barcode'
                            st.rerun()
                        else:
                            st.error(f"❌ Товар с артикулом {task['Артикул/Код OZON']} не найден в остатках!")
                    else:
                        st.error("❌ Задание для указанной ячейки не найдено!")
            else:
                st.warning("⚠️ Введите номер ячейки!")

# Этап 2: Сканирование баркода
elif st.session_state.step == 'scan_barcode':
    st.subheader(f"📍 Отбор ячейки: {st.session_state.cell_number}")
    
    task = st.session_state.current_task
    stock_item = st.session_state.current_stock_item
    
    if task is not None and stock_item is not None:
        # Информация о товаре
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("📦 Товар", task['Наименование товара'])
        with col_info2:
            st.metric("📱 Артикул", task['Артикул/Код OZON'])
        with col_info3:
            st.metric("📊 Кол-во к отбору", task['Кол-во'])

        # Детали из остатков
        with st.expander("ℹ️ Детали товара из остатков"):
            col_det1, col_det2, col_det3 = st.columns(3)
            with col_det1:
                st.write(f"**№ поставки:** {stock_item.get('№ поставки', '')}")
                st.write(f"**№ ГТД:** {stock_item.get('№ ГТД', '')}")
            with col_det2:
                st.write(f"**Длина:** {stock_item.get('Длина', '')}") 
                st.write(f"**Ширина:** {stock_item.get('Ширина', '')}")
                st.write(f"**Высота:** {stock_item.get('Высота', '')}")
            with col_det3:
                st.write(f"**Вес:** {stock_item.get('вес', '')}")
                st.write(f"**Имеи:** {stock_item.get('Имеи', 'Нет')}")

        # Прогресс
        total_to_scan = int(task['Кол-во'])
        scanned_count = len(st.session_state.scanned_barcodes)
        st.progress(scanned_count / total_to_scan if total_to_scan > 0 else 0)
        st.write(f"**Прогресс:** {scanned_count} из {total_to_scan} товаров отсканировано")

        # Блок ввода баркода
        st.subheader("🔊 Шаг 2: Сканируйте баркод")
        barcode_input = st.text_input("Введите или отсканируйте баркод", 
                                     placeholder="Наведите сканер...",
                                     key="barcode_input")
        
        col_scan, col_clear = st.columns([1, 4])
        with col_scan:
            if st.button("✅ Подтвердить сканирование", use_container_width=True):
                if barcode_input:
                    if barcode_input.strip() == str(task['Артикул/Код OZON']).strip():
                        st.session_state.scanned_barcodes.append(barcode_input)
                        st.success(f"✅ Баркод {barcode_input} принят! ({len(st.session_state.scanned_barcodes)}/{total_to_scan})")
                        
                        # Проверяем, нужно ли вводить IMEI
                        has_imei = stock_item.get('Имеи', 'Нет') == 'Да'
                        
                        if has_imei:
                            st.session_state.step = 'enter_imei'
                            st.session_state.entered_imeis = []
                            st.session_state.imei_count = 0
                            # Определяем, сколько IMEI нужно ввести
                            imei1_present = pd.notna(stock_item.get('Имеи1', '')) and stock_item.get('Имеи1', '') != ''
                            imei2_present = pd.notna(stock_item.get('Имеи2', '')) and stock_item.get('Имеи2', '') != ''
                            st.session_state.imei_target = 2 if (imei1_present and imei2_present) else 1
                            st.rerun()
                        else:
                            if len(st.session_state.scanned_barcodes) >= total_to_scan:
                                st.session_state.step = 'finish'
                                st.rerun()
                    else:
                        st.error(f"❌ Неверный баркод! Ожидается: {task['Артикул/Код OZON']}")
                else:
                    st.warning("⚠️ Введите или отсканируйте баркод!")

        with col_clear:
            if total_to_scan == len(st.session_state.scanned_barcodes):
                if st.button("✅ Завершить сканирование", use_container_width=True):
                    st.session_state.step = 'finish'
                    st.rerun()

        # Отсканированные баркоды
        if st.session_state.scanned_barcodes:
            st.write("**Отсканированные баркоды:**")
            for i, bc in enumerate(st.session_state.scanned_barcodes, 1):
                st.write(f"{i}. {bc} ✅")
    else:
        st.error("Ошибка: данные задания не найдены.")
        if st.button("🔄 Начать сначала"):
            st.session_state.step = 'input_cell'
            st.rerun()

# Этап 3: Ввод IMEI
elif st.session_state.step == 'enter_imei':
    st.subheader(f"📱 Шаг 3: Введите IMEI для товара")
    st.write(f"Товар: {st.session_state.current_task['Наименование товара']}")
    
    stock_item = st.session_state.current_stock_item
    imei_target = st.session_state.get('imei_target', 1)
    current_imei_count = len(st.session_state.entered_imeis)
    
    if current_imei_count < imei_target:
        st.write(f"**Введите IMEI {current_imei_count + 1} из {imei_target}**")
        imei_input = st.text_input(f"IMEI #{current_imei_count + 1}", 
                                  placeholder="Введите 15 цифр...",
                                  key="imei_input")
        
        if st.button("✅ Подтвердить IMEI", use_container_width=True):
            if imei_input:
                if re.match(r'^\d{15}$', imei_input):
                    st.session_state.entered_imeis.append(imei_input)
                    st.success(f"✅ IMEI {imei_input} принят!")
                    
                    if len(st.session_state.entered_imeis) >= imei_target:
                        st.session_state.step = 'finish'
                        st.rerun()
                    else:
                        st.rerun()
                else:
                    st.error("❌ Неверный формат IMEI! Должно быть 15 цифр.")
            else:
                st.warning("⚠️ Введите IMEI!")

# Этап 4: Завершение задания
elif st.session_state.step == 'finish':
    st.subheader(f"🎉 Отбор ячейки {st.session_state.cell_number} завершен!")
    
    task = st.session_state.current_task
    stock_item = st.session_state.current_stock_item
    
    completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    imei1 = st.session_state.entered_imeis[0] if len(st.session_state.entered_imeis) > 0 else ""
    imei2 = st.session_state.entered_imeis[1] if len(st.session_state.entered_imeis) > 1 else ""
    
    completed_record = {
        'Номер заказа': task['Номер заказа'],
        'Наименование товара': task['Наименование товара'],
        'Артикул/Код OZON': task['Артикул/Код OZON'],
        'Кол-во': task['Кол-во'],
        '№ поставки': stock_item.get('№ поставки', ''),
        '№ ГТД': stock_item.get('№ ГТД', ''),
        'Имеи': stock_item.get('Имеи', 'Нет'),
        'Длина': stock_item.get('Длина', ''),
        'Ширина': stock_item.get('Ширина', ''),
        'Высота': stock_item.get('Высота', ''),
        'вес': stock_item.get('вес', ''),
        'Имеи1': imei1,
        'Имеи2': imei2,
        'Время отбора': completion_time,
        'Место': st.session_state.cell_number
    }
    
    st.session_state.completed_tasks.append(completed_record)
    
    st.success("✅ Задание успешно выполнено!")
    
    with st.expander("📄 Детали выполненного задания", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Заказ:** {task['Номер заказа']}")
            st.write(f"**Товар:** {task['Наименование товара']}")
            st.write(f"**Артикул:** {task['Артикул/Код OZON']}")
            st.write(f"**Кол-во:** {task['Кол-во']}")
        with col2:
            st.write(f"**Место:** {st.session_state.cell_number}")
            st.write(f"**Время:** {completion_time}")
            if imei1:
                st.write(f"**IMEI1:** {imei1}")
            if imei2:
                st.write(f"**IMEI2:** {imei2}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📋 Следующее задание", use_container_width=True):
            st.session_state.step = 'input_cell'
            st.session_state.current_task = None
            st.session_state.current_stock_item = None
            st.rerun()
    with col2:
        if st.button("📊 Показать отчет", use_container_width=True):
            st.session_state.step = 'show_report'
            st.rerun()
    with col3:
        if st.button("🚪 Завершить", use_container_width=True):
            st.session_state.step = 'show_report'
            st.rerun()

# Этап 5: Отчет
elif st.session_state.step == 'show_report':
    st.subheader("📊 Отчет по выполненным заданиям")
    
    if st.session_state.completed_tasks:
        report_df = pd.DataFrame(st.session_state.completed_tasks)
        st.dataframe(report_df, use_container_width=True, hide_index=True)
        
        # Сохранение в Google Sheets
        if st.button("💾 Сохранить отчет в Google Sheets", use_container_width=True):
            if not st.session_state.use_test_data:
                try:
                    sh = connect_to_gsheet()
                    if sh:
                        report_name = f"Отчет_{datetime.now().strftime('%Y-%m-%d')}"
                        try:
                            worksheet = sh.add_worksheet(title=report_name, rows="1000", cols="20")
                        except:
                            sh.del_worksheet(sh.worksheet(report_name))
                            worksheet = sh.add_worksheet(title=report_name, rows="1000", cols="20")
                        
                        headers = list(report_df.columns)
                        worksheet.append_row(headers)
                        for _, row in report_df.iterrows():
                            worksheet.append_row(row.astype(str).tolist())
                        
                        st.success(f"✅ Отчет сохранен в вкладку '{report_name}'!")
                    else:
                        st.error("❌ Нет подключения к Google Sheets")
                except Exception as e:
                    st.error(f"❌ Ошибка сохранения: {e}")
            else:
                st.warning("⚠️ В тестовом режиме сохранение в Google Sheets недоступно")
        
        # Скачивание CSV
        csv = report_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать отчет в CSV",
            data=csv,
            file_name=f"отчет_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("📭 Нет выполненных заданий для отчета.")
    
    if st.button("🔄 Начать новую смену", use_container_width=True):
        st.session_state.step = 'input_cell'
        st.session_state.completed_tasks = []
        st.rerun()

# --- СТИЛИ ---
st.markdown("""
<style>
    .stTextInput input:focus {
        border-color: #4CAF50 !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.5) !important;
    }
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
    }
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)
