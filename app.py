import streamlit as st
import os
from main import run_capex_agent  # Ваш ReAct агент
from pathlib import Path

st.title("🧠 CapEx AI Аналитик (Qwen2.5)")
st.markdown("Загрузите Excel/PDF → Выберите задачу → Получите отчёт")

# Загрузка файлов
uploaded_files = st.file_uploader("📁 inputs/ (Excel/PDF)", accept_multiple=True)
if uploaded_files:
    inputs_dir = Path("inputs")
    inputs_dir.mkdir(exist_ok=True)
    for file in uploaded_files:
        with open(inputs_dir / file.name, "wb") as f:
            f.write(file.read())
    st.success("✅ Файлы загружены!")

# Выбор задачи (кнопки)
task = st.selectbox(
    "Задача:",
    [
        "Полный анализ сметы",
        "Факторный анализ отклонений",
        "План/факт таблица",
        "Таблица ликвидности",
        "Расчёт себестоимости",
        "Диаграмма-водопад",
    ],
)

if st.button("🚀 Запустить анализ"):
    query = task
    filepath = run_capex_agent(query)

    # Скачивание Excel
    with open(filepath, "rb") as f:
        st.download_button(
            label="📥 Скачать Excel отчёт",
            data=f.read(),
            file_name=Path(filepath).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    st.success(f"Готово: {Path(filepath).name}")

if __name__ == "__main__":
    pass  # streamlit run app.py
