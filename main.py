import os
import re
import json
import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field

from tools.document_parser import parse_inputs
from tools.excel_report import generate_capex_excel
from tools.report_generator import generate_report_summary


# =========================
# Config
# =========================
load_dotenv()

CONFIG_PATH = Path("config.yaml")
DEFAULT_CONFIG = {
    "model": "qwen2.5:7b-instruct-q5_K_M",
    "ollama_base": "http://localhost:11434",
    "output_dir": "outputs",
    "triggers": [
        "проанализируй смету",
        "анализ сметы",
        "факторный анализ",
        "отклонений",
        "план/факт",
        "план факт",
        "ликвидность",
        "себестоимость",
        "диаграмма-водопад",
        "водопад",
        "доклад",
        "текст доклада",
        "резюме",
        "полный анализ",
        "составь таблицу",
        "сравнительная таблица",
    ],
}

if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    config = {**DEFAULT_CONFIG, **loaded}
else:
    config = DEFAULT_CONFIG


# =========================
# Models
# =========================

router_temp = config.get("temperature", {}).get("router", 0.1)
analyst_temp = config.get("temperature", {}).get("analyst", 0.1)
writer_temp = config.get("temperature", {}).get("writer", 0.3)

llm = ChatOllama(
    model=config["model"],
    base_url=config["ollama_base"],
    temperature=analyst_temp,
)

humanizer_llm = ChatOllama(
    model=config["model"],
    base_url=config["ollama_base"],
    temperature=writer_temp,
)


# =========================
# Structured schema
# =========================
class TaskPlan(BaseModel):
    """План выполнения запроса"""

    intent: str = Field(
        description="smeta|variance_factor|plan_fact|liquidity|costing|waterfall|report|full_report|clarify"
    )
    full_report: bool = Field(default=False, description="Нужен полный Excel со всеми листами")
    need_report_text: bool = Field(default=False, description="Нужен текст доклада/резюме")
    need_excel: bool = Field(default=True, description="Нужен Excel на выходе")
    sheet_name: str = Field(default="report", description="Имя выходного файла/листа")
    clarification_question: str = Field(default="", description="Уточняющий вопрос, если данных или формулировки недостаточно")


# =========================
# Guardrails
# =========================
SYSTEM_PROMPT = """
Ты — финансовый аналитик для CapEx/план-факт/ликвидности/себестоимости.

Правила работы:
1. Используй только данные из загруженных файлов и результаты инструментов.
2. Никогда не придумывай и не достраивай цифры, если их нет.
3. Если данных недостаточно, задай уточняющий вопрос пользователю.
4. Если пользователь просит доклад, формируй текст только по фактам из входных данных.
5. Если нет файлов или они пустые, прямо сообщи об этом.
6. Не подменяй расчёты художественным текстом.
"""


# =========================
# Tools for ReAct
# =========================
tools = [parse_inputs]
agent = create_react_agent(llm, tools, state_modifier=SYSTEM_PROMPT)


# =========================
# Helpers
# =========================
def _clean_json(text: str) -> str:
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return text


def _safe_json_load(text: str):
    try:
        return json.loads(_clean_json(text))
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
        return None


def _ensure_output_dir():
    output_dir = Path(config.get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _has_trigger(query: str) -> bool:
    q = (query or "").lower().strip()
    return any(t in q for t in config.get("triggers", []))


def _parse_inputs_safe(query: str, logs: list):
    try:
        raw = parse_inputs.invoke(query) if hasattr(parse_inputs, "invoke") else parse_inputs(query)
        logs.append(f"parse_inputs_ok={bool(raw)}")
        return raw
    except Exception as e:
        logs.append(f"parse_inputs_error={e}")
        return None


def _inputs_missing(raw_inputs) -> bool:
    if raw_inputs is None:
        return True
    if isinstance(raw_inputs, str):
        stripped = raw_inputs.strip()
        if not stripped:
            return True
        if stripped == "{}":
            return True
        if "ОШИБКА" in stripped.upper():
            return True
    if isinstance(raw_inputs, dict) and len(raw_inputs) == 0:
        return True
    return False


def _route_query(query: str, raw_inputs, logs: list) -> dict:
    router_prompt = f"""
Определи план обработки пользовательского запроса.

Запрос:
{query}

Доступные intent:
- smeta
- variance_factor
- plan_fact
- liquidity
- costing
- waterfall
- report
- full_report
- clarify

Правила:
1. Если пользователь просит "полный анализ", выбери full_report.
2. Если просит текст доклада, резюме, объяснение по таблице — need_report_text=true.
3. Если формулировка неясна или данных недостаточно, выбери intent=clarify и задай clarification_question.
4. Если пользователь просит диаграмму-водопад — intent=waterfall.
5. Если пользователь просит только текст без Excel, можно поставить need_excel=true всё равно, если это аналитический сценарий; но если явно только текст, оставь need_excel=false.
6. Отвечай только JSON.

Контекст по данным:
{raw_inputs}
"""
    try:
        structured_llm = llm.with_structured_output(TaskPlan)
        plan = structured_llm.invoke(router_prompt)
        if hasattr(plan, "dict"):
            result = plan.dict()
        else:
            result = dict(plan)
        logs.append(f"router_structured={result}")
        return result
    except Exception as e:
        logs.append(f"router_structured_error={e}")

    fallback_response = llm.invoke(router_prompt).content
    parsed = _safe_json_load(fallback_response)
    if parsed:
        logs.append(f"router_fallback_json={parsed}")
        return parsed

    q = query.lower()
    guessed = {
        "intent": "smeta",
        "full_report": False,
        "need_report_text": False,
        "need_excel": True,
        "sheet_name": "report",
        "clarification_question": "",
    }

    if "полный" in q:
        guessed["intent"] = "full_report"
        guessed["full_report"] = True
        guessed["sheet_name"] = "full_report"
    elif "доклад" in q or "резюме" in q or "текст" in q:
        guessed["intent"] = "report"
        guessed["need_report_text"] = True
        guessed["sheet_name"] = "report_text"
    elif "водопад" in q:
        guessed["intent"] = "waterfall"
        guessed["sheet_name"] = "waterfall"
    elif "ликвид" in q:
        guessed["intent"] = "liquidity"
        guessed["sheet_name"] = "liquidity"
    elif "себесто" in q:
        guessed["intent"] = "costing"
        guessed["sheet_name"] = "costing"
    elif "план/факт" in q or "план факт" in q:
        guessed["intent"] = "plan_fact"
        guessed["sheet_name"] = "plan_fact"
    elif "фактор" in q or "отклонен" in q:
        guessed["intent"] = "variance_factor"
        guessed["sheet_name"] = "variance_factor"

    logs.append(f"router_guessed={guessed}")
    return guessed


def _needs_clarification(plan: dict) -> bool:
    return plan.get("intent") == "clarify" or bool(plan.get("clarification_question"))


def _extract_waterfall_hint(agent_result, raw_inputs) -> str:
    if isinstance(agent_result, dict):
        text = json.dumps(agent_result, ensure_ascii=False)
    else:
        text = str(agent_result)

    candidates = [
        "снижение объема производства",
        "рост бюджета",
        "снижение выручки",
        "рост себестоимости",
        "изменение цен",
    ]
    for c in candidates:
        if c in text.lower():
            return c
    return "ключевое отклонение определяется по данным файла"


def _react_analysis(query: str, raw_inputs, logs: list):
    prompt = f"""
Выполни анализ запроса пользователя только на основе данных ниже.
Если данных недостаточно — явно укажи это.

Запрос:
{query}

Данные:
{raw_inputs}
"""
    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        logs.append("react_analysis_ok=True")
        return result
    except Exception as e:
        logs.append(f"react_analysis_error={e}")
        return {"error": str(e)}


def _humanize_report(query: str, raw_inputs, plan: dict, waterfall_key: str, logs: list) -> str:
    try:
        tool_result = generate_report_summary(raw_inputs, plan, waterfall_key)
        if isinstance(tool_result, str) and tool_result.strip():
            logs.append("report_generator_ok=True")
            return tool_result
    except Exception as e:
        logs.append(f"report_generator_error={e}")

    fallback_prompt = f"""
Подготовь краткий профессиональный доклад на русском языке.
Используй только факты из данных ниже. Ничего не придумывай.
Если не хватает данных, прямо укажи это.

Структура:
1. Исходные параметры проекта
2. Фактические результаты
3. Основные отклонения
4. Ключевой фактор
5. Вывод

Запрос пользователя:
{query}

Данные:
{raw_inputs}

Ключевой фактор:
{waterfall_key}
"""
    try:
        text = humanizer_llm.invoke(fallback_prompt).content
        logs.append("report_humanizer_ok=True")
        return text
    except Exception as e:
        logs.append(f"report_humanizer_error={e}")
        return "Недостаточно данных для подготовки текстового доклада. Загрузите исходные файлы или уточните запрос."


# =========================
# Public API for app.py
# =========================
def run_capex_agent_with_chat(query: str):
    """
    Возвращает:
    (filepath, report_text, logs)

    filepath: str | None
    report_text: str
    logs: list[str]
    """
    logs = []
    _ensure_output_dir()

    query = (query or "").strip()
    logs.append(f"query={query}")

    if not query:
        return None, "Пожалуйста, введите запрос.", logs

    raw_inputs = _parse_inputs_safe(query, logs)

    if _inputs_missing(raw_inputs):
        return (
            None,
            "⚠️ Данные не найдены. Загрузите Excel/PDF в боковую панель. Я не буду придумывать цифры без файлов.",
            logs,
        )

    if not _has_trigger(query):
        return (
            None,
            "Я не распознал задачу. Напишите, например: 'сделай план/факт', 'подготовь доклад', 'построй диаграмму-водопад' или 'полный анализ сметы'.",
            logs,
        )

    logs.append("trigger_detected=True")

    plan = _route_query(query, raw_inputs, logs)

    if _needs_clarification(plan):
        clarification = plan.get("clarification_question") or (
            "Уточните, пожалуйста, какой именно результат нужен: полный Excel, отдельная таблица, диаграмма-водопад или текст доклада?"
        )
        logs.append(f"clarification_needed={clarification}")
        return None, clarification, logs

    react_result = _react_analysis(query, raw_inputs, logs)

    filepath = None
    report_text = ""

    need_excel = plan.get("need_excel", True)
    need_report_text = plan.get("need_report_text", False)

    if plan.get("intent") == "full_report":
        plan["full_report"] = True
        need_excel = True

    if need_excel:
        try:
            filepath = generate_capex_excel(query, raw_inputs, plan)
            logs.append(f"excel_generated={filepath}")
        except Exception as e:
            logs.append(f"excel_generation_error={e}")
            filepath = None

    if need_report_text or any(x in query.lower() for x in ["доклад", "текст", "резюме", "объясни", "прокомментируй"]):
        waterfall_key = _extract_waterfall_hint(react_result, raw_inputs)
        report_text = _humanize_report(query, raw_inputs, plan, waterfall_key, logs)

    if not filepath and not report_text:
        return None, "Не удалось сформировать результат. Проверьте структуру входных файлов и формулировку запроса.", logs

    if not report_text and filepath:
        report_text = "Результат подготовлен. Excel-файл доступен для скачивания."

    return filepath, report_text, logs


# =========================
# CLI mode
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="Запрос для CapEx-агента")
    args = parser.parse_args()

    result_path, result_text, result_logs = run_capex_agent_with_chat(args.query)

    print("\n=== RESULT ===")
    print("FILE:", result_path)
    print("TEXT:", result_text)
    print("LOGS:")
    for line in result_logs:
        print("-", line)