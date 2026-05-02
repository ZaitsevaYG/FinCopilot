import streamlit as st
import os
from pathlib import Path

# Конфигурация темы и CSS
st.set_page_config(page_title="АГРОЭКО: ФинАналитик", layout="wide")

st.markdown("""
<style>
    /* Шрифты: PT Sans Narrow и Helios Condensed аналоги (набор системных) */
    :root {
        --deep-green: #003f0b;
        --light-green: #87C800;
        --add-green: #195532;
        --gray: #828282;
    }
    
    html, body, [class*="css"] {
        font-family: 'PT Sans Narrow', 'Arial Narrow', Arial, sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'HeliosCond', 'Impact', sans-serif; /* Helios-подобный */
        color: var(--deep-green);
    }

    /* Основной фон белый */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Сайдбар */
    [data-testid="stSidebar"] {
        background-color: #f4f4f4;
        border-right: 1px solid #e0e0e0;
    }

    /* Лого-плейсхолдер */
    .logo-container {
        padding: 20px;
        text-align: center;
        background-color: white;
        margin-bottom: 20px;
    }

    /* Кнопки в корпоративных цветах */
    .stButton > button {
        background-color: var(--light-green) !important;
        color: white !important;
        border: none !important;
        border-radius: 4px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: var(--add-green) !important;
    }

    /* Чат-интерфейс */
    .stChatMessage {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    .stChatMessage.user {
        background-color: #f9f9f9;
        color: var(--deep-green);
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    st.image("assets/image.jpg", width=200) 
    st.markdown('</div>', unsafe_allow_html=True)
    st.title("FinCopilot")
    st.markdown("---")

# Загрузка
uploaded_files = st.file_uploader("📁 inputs/ (Excel/PDF)", accept_multiple=True)
if uploaded_files:
    inputs_dir = Path("inputs")
    inputs_dir.mkdir(exist_ok=True)
    for file in uploaded_files:
        with open(inputs_dir / file.name, "wb") as f:
            f.write(file.read())
    st.success("✅ Файлы загружены!")

# Запрос
col1, col2 = st.columns(2)
with col1:
    task = st.selectbox("Шаблон:", [
        "Проанализируй смету",
        "Факторный анализ отклонений", 
        "Сравнительная таблица план/факт",
        "Таблица ликвидности проекта",
        "Таблица расчета себестоимости",
        "Построй диаграмму-водопад отклонений",
        "Полный анализ сметы"
    ])
with col2:
    custom_query = st.text_input("Или свой запрос:", value=task)

query = custom_query or task

if st.button("🚀 Запустить ФинАгента", type="primary"):
    with st.spinner("Агент думает..."):
        filepath = run_capex_agent(query)
    
    # Скачать
    with open(filepath, "rb") as f:
        st.download_button(
            label=f"📥 {Path(filepath).name}",
            data=f.read(),
            file_name=Path(filepath).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    st.success(f"✅ Готово!")