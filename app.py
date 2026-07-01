import streamlit as st
import pandas as pd
from datetime import datetime
import re

# --- ТЕСТОВЫЕ ДАННЫЕ (чтобы сразу работало) ---
def get_test_data():
    """Тестовые данные для демонстрации работы"""
    tasks_data = {
        'Номер заказа': ['0153567258-0108-1', '19346551-0329-1', '50156854-0038-1'],
        'Артикул/Код OZON': ['195950627503', '195950543667', '195950643442'],
        'Наименование товара': ['iPhone 17 pro 256GB', 'AirPods pro 3', 'iPhone 17 256GB black'],
        'Место': ['2HM1-1-1-1001', '2HM1-1-1-1004', '2HM1-1-1-2103'],
        'Кол-во': [1, 1, 1]
    }
    tasks_df = pd.DataFrame(tasks_data)
    
    stock_data = {
        'Место': ['2HM1-1-1-1001', '2HM1-1-1-1004', '2HM1-1-1-2103'],
        'Наименование товара': ['iPhone 17 pro 256GB', 'AirPods pro 3', 'iPhone 17 256GB black'],
        'Артикул/Код OZON': ['195950627503', '195950543667', '195950643442'],
        'Кол-во': [5, 3, 2],
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
st.set_page_config(page_title="Сборка", layout="centered")

# Состояние сессии
if 'tasks_df' not in st.session_state:
    st.session_state.tasks_df, st.session_state.stock_df = get_test_data()
if 'step' not in st.session_state:
    st.session_state.step = 'main'  # main, scan, imei, finish
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

# --- ФУНКЦИИ ---
def find_task(cell):
    """Находит задание по ячейке"""
    try:
        task = st.session_state.tasks_df[st.session_state.tasks_df['Место'].astype(str).str.strip() == str(cell).strip()]
        return task.iloc[0] if not task.empty else None
    except:
        return None

def find_stock(article):
    """Находит товар в остатках по артикулу"""
    try:
        items = st.session_state.stock_df[st.session_state.stock_df['Артикул/Код OZON'].astype(str).str.strip() == str(article).strip()]
        return items.iloc[0] if not items.empty else None
    except:
        return None

# --- СТИЛИ ДЛЯ ТЕЛЕФОНА ---
st.markdown("""
<style>
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
    }
    /* Большие заголовки */
    h1 {
        font-size: 40px !important;
        text-align: center !important;
    }
    h2 {
        font-size: 32px !important;
        text-align: center !important;
    }
    h3 {
        font-size: 28px !important;
        text-align: center !important;
    }
    /* Крупный текст */
    p, div, span, label {
        font-size: 22px !important;
    }
    /* Метрики */
    [data-testid="metric-container"] {
        background: #f0f2f6;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        text-align: center;
    }
    /* Прогресс-бар */
    .stProgress > div > div {
        height: 30px !important;
    }
    /* Карточки */
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
    
    if st.button("📋 Список заданий", use_container_width=True):
        st.session_state.step = 'main'
        st.rerun()
    
    if st.button("📊 Отчет", use_container_width=True):
        st.session_state.step = 'report'
        st.rerun()
    
    st.divider()
    
    # Показываем статистику
    total_tasks = len(st.session_state.tasks_df) if st.session_state.tasks_df is not None else 0
    done_tasks = len(st.session_state.completed)
    st.metric("📦 Заданий", f"{done_tasks}/{total_tasks}")
    
    if st.button("🔄 Сбросить всё", use_container_width=True):
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
    
    # Показываем список заданий
    if st.session_state.tasks_df is not None and not st.session_state.tasks_df.empty:
        st.subheader("📋 Доступные задания")
        
        for idx, row in st.session_state.tasks_df.iterrows():
            # Проверяем, выполнено ли задание
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
                            task = find_task(row['Место'])
                            if task is not None:
                                stock = find_stock(task['Артикул/Код OZON'])
                                if stock is not None:
                                    st.session_state.current_task = task
                                    st.session_state.current_stock = stock
                                    st.session_state.scanned = []
                                    st.session_state.imeis = []
                                    st.session_state.step = 'scan'
                                    st.rerun()
                    else:
                        st.success("✅")
    else:
        st.warning("⚠️ Нет заданий")
        if st.button("📥 Загрузить тестовые данные"):
            st.session_state.tasks_df, st.session_state.stock_df = get_test_data()
            st.rerun()

# --- СКАНИРОВАНИЕ ---
elif st.session_state.step == 'scan':
    task = st.session_state.current_task
    stock = st.session_state.current_stock
    
    if task is None:
        st.error("Ошибка")
        if st.button("Назад"):
            st.session_state.step = 'main'
            st.rerun()
    else:
        # Информация
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
                if stock.get('Имеи', 'Нет') == 'Да':
                    st.session_state.imeis = []
                    st.session_state.step = 'imei'
                    st.rerun()
                else:
                    if len(st.session_state.scanned) >= total:
                        st.session_state.step = 'finish'
                        st.rerun()
                    else:
                        # Очищаем поле
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
    
    # Определяем сколько IMEI
    has_imei1 = pd.notna(stock.get('Имеи1', '')) and stock.get('Имеи1', '') != ''
    has_imei2 = pd.notna(stock.get('Имеи2', '')) and stock.get('Имеи2', '') != ''
    
    current = len(st.session_state.imeis)
    
    if current == 0:
        st.write("**Введите IMEI 1**")
        label = "IMEI 1"
    elif has_imei1 and has_imei2 and current == 1:
        st.write("**Введите IMEI 2 (или 0)**")
        label = "IMEI 2"
    else:
        st.session_state.step = 'finish'
        st.rerun()
    
    imei_input = st.text_input(label, placeholder="15 цифр или 0", key="imei_input")
    
    if imei_input:
        if imei_input == '0' or re.match(r'^\d{15}$', imei_input):
            st.session_state.imeis.append(imei_input)
            st.success(f"✅ IMEI {len(st.session_state.imeis)} сохранен")
            
            # Проверяем нужно ли еще
            if has_imei1 and has_imei2 and len(st.session_state.imeis) < 2:
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
    
    st.balloons()
    st.success("✅ Готово!")
    
    # Сохраняем
    record = {
        'Номер заказа': task['Номер заказа'],
        'Наименование товара': task['Наименование товара'],
        'Артикул/Код OZON': task['Артикул/Код OZON'],
        'Кол-во': task['Кол-во'],
        '№ поставки': st.session_state.current_stock.get('№ поставки', ''),
        '№ ГТД': st.session_state.current_stock.get('№ ГТД', ''),
        'Имеи': st.session_state.current_stock.get('Имеи', 'Нет'),
        'Длина': st.session_state.current_stock.get('Длина', ''),
        'Ширина': st.session_state.current_stock.get('Ширина', ''),
        'Высота': st.session_state.current_stock.get('Высота', ''),
        'вес': st.session_state.current_stock.get('вес', ''),
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
        
        # Скачать
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Скачать CSV", csv, f"отчет_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        
        st.caption(f"Всего выполнено: {len(df)} заданий")
    else:
        st.info("Нет выполненных заданий")
    
    if st.button("🔙 На главную", use_container_width=True):
        st.session_state.step = 'main'
        st.rerun()
