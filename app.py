import streamlit as st
from pathlib import Path
from main import run_capex_agent_with_chat

# =========================
# Page config
# =========================
st.set_page_config(
    page_title="АГРОЭКО: ФинАналитик",
    layout="wide",
    page_icon="📈"
)

# =========================
# Session state
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "tech_logs" not in st.session_state:
    st.session_state.tech_logs = []

if "uploaded_names" not in st.session_state:
    st.session_state.uploaded_names = []

# =========================
# Corporate CSS
# =========================
st.markdown("""
<style>
    :root {
        --deep-green: #003f0b;
        --light-green: #87C800;
        --extra-green: #195532;
        --gray: #828282;
        --soft-gray: #f5f5f5;
        --line-gray: #e7e7e7;
        --white: #ffffff;
        --black: #000000;
    }

    .stApp {
        background: var(--white);
        color: var(--black);
    }

    html, body, [class*="css"] {
        font-family: Arial, "PT Sans Narrow", sans-serif;
    }

    h1, h2, h3, h4 {
        color: var(--deep-green);
        font-family: Arial, "PT Sans Narrow", sans-serif;
        font-weight: 700;
        letter-spacing: 0.2px;
    }

    [data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid var(--line-gray);
    }

    .logo-wrap {
        padding: 6px 0 12px 0;
        text-align: center;
    }

    .hero-box {
        background: linear-gradient(180deg, #ffffff 0%, #fbfdf9 100%);
        border: 1px solid var(--line-gray);
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }

    .helper-box {
        background: var(--soft-gray);
        border-left: 4px solid var(--light-green);
        border-radius: 10px;
        padding: 12px 14px;
        margin: 10px 0 18px 0;
        color: #2a2a2a;
    }

    div.stButton > button {
        background-color: var(--light-green) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1rem !important;
    }

    div.stButton > button:hover {
        background-color: var(--extra-green) !important;
        color: white !important;
    }

    [data-testid="stDownloadButton"] > button {
        background-color: var(--deep-green) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    [data-testid="stDownloadButton"] > button:hover {
        background-color: var(--extra-green) !important;
        color: white !important;
    }

    .stChatMessage {
        border: 1px solid var(--line-gray);
        border-radius: 14px;
        padding: 6px;
        background: #ffffff;
    }

    .metric-chip {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #f3f8ed;
        color: var(--deep-green);
        border: 1px solid #dce8cf;
        font-size: 13px;
        margin-right: 8px;
        margin-bottom: 8px;
    }

    .small-note {
        color: var(--gray);
        font-size: 0.92rem;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Sidebar
# =========================
with st.sidebar:
    st.markdown('<div class="logo-wrap">', unsafe_allow_html=True)
    logo_path = Path("assets/image.jpg")
    if logo_path.exists():
        st.image(str(logo_path), width=170)
    else:
        st.markdown(
            """
            <div style="
                height:120px;
                border:1px dashed #87C800;
                border-radius:12px;
                display:flex;
                align-items:center;
                justify-content:center;
                color:#828282;
                background:#ffffff;">
                Лого placeholder
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### FinCopilot")
    st.caption("CapEx / план-факт / ликвидность / доклады")

    uploaded_files = st.file_uploader(
        "Загрузить данные (Excel/PDF)",
        accept_multiple_files=True,
        type=["xlsx", "xls", "pdf"]
    )

    if uploaded_files:
        inputs_dir = Path("inputs")
        inputs_dir.mkdir(exist_ok=True)

        saved_names = []
        for file in uploaded_files:
            file_path = inputs_dir / file.name
            with open(file_path, "wb") as f:
                f.write(file.read())
            saved_names.append(file.name)

        st.session_state.uploaded_names = saved_names
        st.success("✅ Файлы загружены")

    if st.session_state.uploaded_names:
        st.markdown("**Загруженные файлы:**")
        for name in st.session_state.uploaded_names:
            st.markdown(f"- {name}")

    st.markdown("---")

    st.markdown("**Быстрые запросы:**")
    quick_queries = [
        "Проанализируй смету",
        "Составь факторный анализ отклонений",
        "Составь сравнительную таблицу план/факт",
        "Составь таблицу ликвидности проекта",
        "Составь таблицу расчета себестоимости",
        "Построй диаграмму-водопад отклонений",
        "Подготовь текст доклада по данным проекта",
    ]

    for qq in quick_queries:
        if st.button(qq, key=f"quick_{qq}"):
            st.session_state.messages.append({"role": "user", "content": qq})
            st.rerun()

    st.markdown("---")

    if st.button("🔄 Очистить чат"):
        st.session_state.messages = []
        st.session_state.tech_logs = []
        st.rerun()

# =========================
# Main header
# =========================
st.markdown(
    """
    <div class="hero-box">
        <h1 style="margin-bottom:8px;">📈 АГРОЭКО: ФинАналитик</h1>
        <div class="small-note">
            Чат для анализа смет, план/факт, факторных отклонений, ликвидности,
            себестоимости, диаграммы-водопада и подготовки текста доклада.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="helper-box">
        ИИ должен работать только по данным из загруженных файлов.
        Если данных не хватает, он должен сначала задать уточняющий вопрос, а не придумывать цифры.
    </div>
    """,
    unsafe_allow_html=True
)

chip_col1, chip_col2, chip_col3 = st.columns(3)
with chip_col1:
    st.markdown('<span class="metric-chip">Excel-only результат</span>', unsafe_allow_html=True)
with chip_col2:
    st.markdown('<span class="metric-chip">Доклад + хуманизация текста</span>', unsafe_allow_html=True)
with chip_col3:
    st.markdown('<span class="metric-chip">Уточняющие вопросы в чате</span>', unsafe_allow_html=True)

# =========================
# Chat history
# =========================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# =========================
# Prompt processing helper
# =========================
def process_user_prompt(user_prompt: str):
    with st.chat_message("user"):
        st.markdown(user_prompt)

    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        with st.spinner("Агент анализирует данные..."):
            try:
                result = run_capex_agent_with_chat(user_prompt)

                # Поддержка формата:
                # (filepath, report_text)
                # или (filepath, report_text, logs)
                if isinstance(result, tuple):
                    if len(result) == 3:
                        filepath, report_text, logs = result
                    elif len(result) == 2:
                        filepath, report_text = result
                        logs = []
                    else:
                        filepath = None
                        report_text = "⚠️ Неожиданный формат ответа от main.py"
                        logs = []
                else:
                    filepath = None
                    report_text = "⚠️ main.py вернул некорректный результат"
                    logs = []

                st.session_state.tech_logs = logs if isinstance(logs, list) else [str(logs)]

                response_parts = []

                if report_text:
                    response_parts.append(f"**📝 Доклад / ответ:**\n\n{report_text}")

                if filepath and Path(filepath).exists():
                    response_parts.append("✅ Excel-отчёт подготовлен.")
                elif not report_text:
                    response_parts.append("⚠️ Отчёт не был сформирован.")

                final_response = "\n\n".join(response_parts)
                st.markdown(final_response)

                if filepath and Path(filepath).exists():
                    with open(filepath, "rb") as f:
                        st.download_button(
                            label="📥 Скачать Excel-отчёт",
                            data=f.read(),
                            file_name=Path(filepath).name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch"
                        )

                with st.expander("🛠 Техническая информация"):
                    if filepath:
                        st.code(f"Файл результата: {filepath}")
                    else:
                        st.code("Файл результата не сформирован")

                    st.code("Модель: qwen2.5:7b-instruct-q5_K_M через Ollama")

                    if st.session_state.uploaded_names:
                        st.markdown("**Файлы в контексте:**")
                        for name in st.session_state.uploaded_names:
                            st.markdown(f"- {name}")
                    else:
                        st.warning("Файлы не загружены")

                    if st.session_state.tech_logs:
                        st.markdown("**Логи:**")
                        for item in st.session_state.tech_logs:
                            st.code(str(item))
                    else:
                        st.info("Дополнительные логи не переданы")

                st.session_state.messages.append(
                    {"role": "assistant", "content": final_response}
                )

            except Exception as e:
                error_text = f"⚠️ Ошибка при выполнении анализа: {e}"
                st.error(error_text)

                with st.expander("🛠 Техническая информация"):
                    st.code(str(e))

                st.session_state.messages.append(
                    {"role": "assistant", "content": error_text}
                )

# =========================
# Chat input
# =========================
if prompt := st.chat_input("Напишите запрос, например: 'Подготовь доклад по проекту и приложи Excel'"):
    process_user_prompt(prompt)

# =========================
# Auto-run quick query from sidebar
# =========================
if st.session_state.messages:
    last_msg = st.session_state.messages[-1]
    if (
        last_msg["role"] == "user"
        and len(st.session_state.messages) >= 1
        and (
            len(st.session_state.messages) == 1
            or st.session_state.messages[-2]["role"] != "assistant"
        )
    ):
        process_user_prompt(last_msg["content"])