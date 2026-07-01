import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- НАСТРОЙКА ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS ---
# Используйте секреты Streamlit для безопасного хранения учетных данных
# В файле .streamlit/secrets.toml добавьте:
# [google]
# service_account_key = '{"type": "service_account", ...}'  # Ваш JSON-ключ

def connect_to_gsheet():
    """Подключение к Google Sheets с использованием сервисного аккаунта."""
    try:
        # Получаем ключ из секретов
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["google"]["service_account_key"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Открываем таблицу по ID из ссылки
        sheet_id = "109S4MTu32nb2Ou5JiYEmWxj1urNxLXAc0vZjD5JS-F4"
        return client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---
def load_data():
    """Загружает данные из вкладок 'Отбор' и 'Остатки'."""
    sh = connect_to_gsheet()
    if sh is None:
        return None, None

    try:
        # Загружаем задания из вкладки "Отбор"
        worksheet_tasks = sh.worksheet("Отбор")
        tasks_data = worksheet_tasks.get_all_values()
        if len(tasks_data) > 1:
            tasks_df = pd.DataFrame(tasks_data[1:], columns=tasks_data[0])
        else:
            tasks_df = pd.DataFrame(columns=['Номер заказа', 'Артикул/Код OZON', 'Наименование товара', 'Место', 'Кол-во'])

        # Загружаем остатки из вкладки "Остатки"
        worksheet_stock = sh.worksheet("Остатки")
        stock_data = worksheet_stock.get_all_values()
        if len(stock_data) > 1:
            stock_df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
            # Приводим кол-во к числу
            stock_df['Кол-во'] = pd.to_numeric(stock_df['Кол-во'], errors='coerce')
        else:
            stock_df = pd.DataFrame(columns=['Место', 'Наименование товара', 'Артикул/Код OZON', 'Кол-во', '№ поставки', '№ ГТД', 'Имеи', 'Длина', 'Ширина', 'Высота', 'вес', 'Имеи1', 'Имеи2'])

        return tasks_df, stock_df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return None, None

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

# --- ОСНОВНОЙ ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="Система Сборки Заказов", layout="wide")

# Инициализация состояния сессии
if 'step' not in st.session_state:
    st.session_state.step = 'input_cell'  # Этапы: input_cell, scan_barcode, enter_imei, finish
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
    st.session_state.tasks_df, st.session_state.stock_df = load_data()
if 'completed_tasks' not in st.session_state:
    st.session_state.completed_tasks = []
if 'task_start_time' not in st.session_state:
    st.session_state.task_start_time = None

# --- ЗАГОЛОВОК И ОБНОВЛЕНИЕ ДАННЫХ ---
col1, col2 = st.columns([4, 1])
with col1:
    st.title("📦 Система Сборки Заказов")
with col2:
    if st.button("🔄 Обновить данные", use_container_width=True):
        st.session_state.tasks_df, st.session_state.stock_df = load_data()
        st.rerun()

# --- ОТОБРАЖЕНИЕ ОСТАВШИХСЯ ЗАДАНИЙ ---
with st.expander("📋 Список заданий на сборку"):
    if st.session_state.tasks_df is not None and not st.session_state.tasks_df.empty:
        # Показываем только задания, которые не были выполнены
        # Для простоты, считаем, что все задания активны, пока мы не переместили их в выполненные
        st.dataframe(st.session_state.tasks_df[['Номер заказа', 'Наименование товара', 'Место', 'Кол-во']], use_container_width=True, hide_index=True)
    else:
        st.info("Нет активных заданий.")

# --- ОСНОВНОЙ РАБОЧИЙ ПРОЦЕСС ---
st.divider()

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
                # Ищем задание
                task = find_task_by_cell(st.session_state.tasks_df, cell_input)
                if task is not None:
                    # Проверяем, есть ли товар в остатках
                    stock_items = find_stock_items(st.session_state.stock_df, task['Артикул/Код OZON'])
                    if not stock_items.empty:
                        # Берем первый подходящий товар (по логике, можно уточнить по месту)
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

# Этап 2: Сканирование баркода (и ввод IMEI)
elif st.session_state.step == 'scan_barcode':
    st.subheader(f"📍 Отбор ячейки: {st.session_state.cell_number}")
    
    # Информация о задании
    task = st.session_state.current_task
    stock_item = st.session_state.current_stock_item
    
    if task is not None and stock_item is not None:
        # Отображаем информацию о товаре
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("📦 Товар", task['Наименование товара'])
        with col_info2:
            st.metric("📱 Артикул", task['Артикул/Код OZON'])
        with col_info3:
            st.metric("📊 Кол-во к отбору", task['Кол-во'])

        # Отображаем дополнительную информацию из остатков
        with st.expander("ℹ️ Детали товара из остатков"):
            col_det1, col_det2, col_det3 = st.columns(3)
            with col_det1:
                st.write(f"**№ поставки:** {stock_item['№ поставки']}")
                st.write(f"**№ ГТД:** {stock_item['№ ГТД']}")
            with col_det2:
                st.write(f"**Длина:** {stock_item['Длина']}") 
                st.write(f"**Ширина:** {stock_item['Ширина']}")
                st.write(f"**Высота:** {stock_item['Высота']}")
            with col_det3:
                st.write(f"**Вес:** {stock_item['вес']}")
                st.write(f"**Имеи:** {stock_item['Имеи']}")

        # Прогресс сканирования
        total_to_scan = int(task['Кол-во'])
        scanned_count = len(st.session_state.scanned_barcodes)
        st.progress(scanned_count / total_to_scan if total_to_scan > 0 else 0)
        st.write(f"**Прогресс:** {scanned_count} из {total_to_scan} товаров отсканировано")

        # Блок ввода баркода
        st.subheader("🔊 Шаг 2: Сканируйте баркод")
        barcode_input = st.text_input("Введите или отсканируйте баркод", 
                                     placeholder="Наведите сканер...",
                                     key="barcode_input",
                                     on_change=None)
        
        col_scan, col_clear = st.columns([1, 4])
        with col_scan:
            if st.button("✅ Подтвердить сканирование", use_container_width=True):
                if barcode_input:
                    # Проверяем, совпадает ли баркод с артикулом
                    if barcode_input.strip() == str(task['Артикул/Код OZON']).strip():
                        # Баркод верный
                        st.session_state.scanned_barcodes.append(barcode_input)
                        st.success(f"✅ Баркод {barcode_input} принят! ({len(st.session_state.scanned_barcodes)}/{total_to_scan})")
                        
                        # Проверяем, нужно ли вводить IMEI
                        has_imei = stock_item.get('Имеи', 'Нет') == 'Да'
                        imei1_present = pd.notna(stock_item.get('Имеи1', '')) and stock_item.get('Имеи1', '') != ''
                        imei2_present = pd.notna(stock_item.get('Имеи2', '')) and stock_item.get('Имеи2', '') != ''
                        
                        # Если есть IMEI, переходим к его вводу
                        if has_imei:
                            st.session_state.step = 'enter_imei'
                            st.session_state.entered_imeis = []  # Сбрасываем список введенных IMEI
                            st.session_state.imei_count = 0
                            # Определяем, сколько IMEI нужно ввести (1 или 2)
                            if imei1_present and imei2_present:
                                st.session_state.imei_target = 2
                            else:
                                st.session_state.imei_target = 1
                            st.rerun()
                        else:
                            # Если IMEI не требуется, проверяем, все ли отсканированы
                            if len(st.session_state.scanned_barcodes) >= total_to_scan:
                                st.session_state.step = 'finish'
                                st.rerun()
                    else:
                        st.error(f"❌ Неверный баркод! Ожидается артикул: {task['Артикул/Код OZON']}")
                else:
                    st.warning("⚠️ Введите или отсканируйте баркод!")

        with col_clear:
            # Кнопка для ручного завершения, если сканирование не требуется (например, если товар один, а IMEI нет)
            if total_to_scan == len(st.session_state.scanned_barcodes):
                if st.button("✅ Завершить сканирование (если все товары собраны)", use_container_width=True):
                    st.session_state.step = 'finish'
                    st.rerun()

        # Показываем уже отсканированные баркоды
        if st.session_state.scanned_barcodes:
            st.write("**Отсканированные баркоды:**")
            for i, bc in enumerate(st.session_state.scanned_barcodes, 1):
                st.write(f"{i}. {bc} ✅")
    else:
        st.error("Ошибка: данные задания не найдены. Начните заново.")
        if st.button("🔄 Начать сначала"):
            st.session_state.step = 'input_cell'
            st.rerun()

# Этап 3: Ввод IMEI
elif st.session_state.step == 'enter_imei':
    st.subheader(f"📱 Шаг 3: Введите IMEI для товара")
    st.write(f"Товар: {st.session_state.current_task['Наименование товара']}")
    
    # Определяем, сколько IMEI нужно ввести
    stock_item = st.session_state.current_stock_item
    imei_target = 2 if (pd.notna(stock_item.get('Имеи1', '')) and stock_item.get('Имеи1', '') != '' and 
                        pd.notna(stock_item.get('Имеи2', '')) and stock_item.get('Имеи2', '') != '') else 1
    
    current_imei_count = len(st.session_state.entered_imeis)
    
    if current_imei_count < imei_target:
        st.write(f"**Введите IMEI {current_imei_count + 1} из {imei_target}**")
        imei_input = st.text_input(f"IMEI #{current_imei_count + 1}", 
                                  placeholder="Введите IMEI...",
                                  key="imei_input")
        
        if st.button("✅ Подтвердить IMEI", use_container_width=True):
            if imei_input:
                # Простая валидация IMEI (15 цифр)
                if re.match(r'^\d{15}$', imei_input):
                    st.session_state.entered_imeis.append(imei_input)
                    st.success(f"✅ IMEI {imei_input} принят!")
                    
                    if len(st.session_state.entered_imeis) >= imei_target:
                        # Все IMEI введены
                        st.session_state.step = 'finish'
                        st.rerun()
                    else:
                        # Очищаем поле для ввода следующего IMEI
                        st.rerun()
                else:
                    st.error("❌ Неверный формат IMEI! Должно быть 15 цифр.")
            else:
                st.warning("⚠️ Введите IMEI!")
    else:
        # Если все IMEI введены, переходим к завершению
        st.session_state.step = 'finish'
        st.rerun()

# Этап 4: Завершение задания
elif st.session_state.step == 'finish':
    st.subheader(f"🎉 Отбор ячейки {st.session_state.cell_number} завершен!")
    
    # Собираем данные для записи
    task = st.session_state.current_task
    stock_item = st.session_state.current_stock_item
    
    # Формируем запись для сохранения
    completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Определяем IMEI1 и IMEI2 (если были введены)
    imei1 = st.session_state.entered_imeis[0] if len(st.session_state.entered_imeis) > 0 else ""
    imei2 = st.session_state.entered_imeis[1] if len(st.session_state.entered_imeis) > 1 else ""
    
    # Создаем словарь с данными для сохранения
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
    
    # Отображаем информацию о завершенном задании
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
            st.write(f"**Время завершения:** {completion_time}")
            if imei1:
                st.write(f"**IMEI1:** {imei1}")
            if imei2:
                st.write(f"**IMEI2:** {imei2}")
    
    # Кнопки для продолжения работы
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📋 Следующее задание", use_container_width=True):
            st.session_state.step = 'input_cell'
            st.session_state.current_task = None
            st.session_state.current_stock_item = None
            st.rerun()
    with col2:
        if st.button("📊 Показать отчет по смене", use_container_width=True):
            st.session_state.step = 'show_report'
            st.rerun()
    with col3:
        if st.button("🚪 Завершить работу", use_container_width=True):
            st.session_state.step = 'show_report'
            st.rerun()

# Этап 5: Отчет
elif st.session_state.step == 'show_report':
    st.subheader("📊 Отчет по выполненным заданиям")
    
    if st.session_state.completed_tasks:
        report_df = pd.DataFrame(st.session_state.completed_tasks)
        st.dataframe(report_df, use_container_width=True, hide_index=True)
        
        # Кнопка для сохранения отчета в Google Sheets
        if st.button("💾 Сохранить отчет в Google Sheets", use_container_width=True):
            try:
                sh = connect_to_gsheet()
                if sh:
                    # Создаем вкладку с датой
                    report_name = f"Отчет_{datetime.now().strftime('%Y-%m-%d')}"
                    try:
                        worksheet = sh.add_worksheet(title=report_name, rows="1000", cols="20")
                    except:
                        # Если вкладка уже существует, удаляем и создаем заново
                        sh.del_worksheet(sh.worksheet(report_name))
                        worksheet = sh.add_worksheet(title=report_name, rows="1000", cols="20")
                    
                    # Записываем заголовки и данные
                    headers = list(report_df.columns)
                    worksheet.append_row(headers)
                    for _, row in report_df.iterrows():
                        worksheet.append_row(row.astype(str).tolist())
                    
                    st.success(f"✅ Отчет сохранен в вкладку '{report_name}'!")
                else:
                    st.error("❌ Не удалось подключиться к Google Sheets")
            except Exception as e:
                st.error(f"❌ Ошибка сохранения: {e}")
        
        # Кнопка для скачивания отчета в CSV
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

# --- СТИЛИЗАЦИЯ ДЛЯ УЛУЧШЕННОГО ИНТЕРФЕЙСА ---
st.markdown("""
<style>
    /* Подсветка успешного сканирования */
    .stTextInput input:focus {
        border-color: #4CAF50 !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.5) !important;
    }
    /* Кастомные цвета для кнопок */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
    }
    /* Метрики */
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Подсказки по использованию
with st.sidebar:
    st.header("📖 Инструкция")
    st.markdown("""
    1. **Введите номер ячейки** из задания.
    2. **Сканируйте баркод** товара. При совпадении с артикулом он будет принят.
    3. Если у товара есть IMEI (колонка "Имеи" = "Да"), система попросит ввести его (один или два).
    4. После сканирования всех товаров и ввода IMEI задание завершится.
    5. **Отчет** по всем выполненным заданиям сохраняется в Google Sheets и доступен для скачивания.
    
    **Цветовая индикация:**
    - ✅ Зеленый - успешное сканирование
    - ❌ Красный - ошибка (неверный баркод)
    - ⚠️ Желтый - предупреждение
    """)
    
    if st.button("🗑️ Сбросить все данные сессии"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()