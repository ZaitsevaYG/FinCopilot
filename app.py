import streamlit as st
import os
from main import run_capex_agent
from pathlib import Path

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