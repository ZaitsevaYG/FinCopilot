import streamlit as st
import os
from main import run_capex_agent
from pathlib import Path

st.markdown("""
<style>
    /* Фон градиент + текстура */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        background-attachment: fixed;
    }
    /* Основной контейнер с тенью */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1000px;
        background: rgba(15, 15, 35, 0.95);
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(79, 152, 163, 0.2);
    }
    /* Заголовок */
    h1 {
        color: #4f98a3 !important;
        font-family: 'Segoe UI', sans-serif;
        text-shadow: 0 2px 10px rgba(79,152,163,0.5);
        font-size: 2.5rem !important;
    }
    /* Кнопки */
    .stButton > button {
        background: linear-gradient(45deg, #4f98a3, #227f8b);
        border-radius: 12px;
        border: none;
        color: white;
        font-weight: 600;
        padding: 0.8rem 2rem;
        box-shadow: 0 8px 20px rgba(79,152,163,0.4);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px rgba(79,152,163,0.6);
    }
    /* Файл аплоадер */
    .uploadedFileUploader {
        background: rgba(26, 26, 46, 0.8);
        border-radius: 12px;
        border: 2px dashed #4f98a3;
    }
    /* Selectbox и инпуты */
    .stSelectbox > div > div > div, .stTextArea > div {
        background: rgba(26, 26, 46, 0.9);
        border-radius: 12px;
        border: 1px solid #4f98a3;
    }
    /* Success сообщения */
    .stSuccess {
        background: rgba(67, 122, 34, 0.2);
        border-radius: 12px;
        border-left: 4px solid #6daa45;
    }
    /* Метрики/статус */
    [data-testid="stStatusWidget"] {
        background: rgba(15, 15, 35, 0.7);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 FinCopilot: помощник финансового аналитика")
st.markdown("**Загрузите Excel/PDF → Напишите запрос → Получите Excel**")

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