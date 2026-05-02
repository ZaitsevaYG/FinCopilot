import json
import re
from typing import Any, Dict, List, Tuple

from langchain_ollama import ChatOllama


# =========================
# LLM for humanized report
# =========================
# Температура умеренная: текст живой, но без лишней фантазии.
llm_humanizer = ChatOllama(
    model="qwen2.5:7b-instruct-q5_K_M",
    base_url="http://localhost:11434",
    temperature=0.3,
)


# =========================
# Helpers
# =========================
def _to_python_obj(inputs_data: Any) -> Any:
    if isinstance(inputs_data, (dict, list)):
        return inputs_data

    if isinstance(inputs_data, str):
        text = inputs_data.strip()
        if not text:
            return {}

        try:
            return json.loads(text)
        except Exception:
            return {"raw_text": text}

    return {"raw_text": str(inputs_data)}


def _flatten_numbers(obj: Any, path: str = "") -> List[Tuple[str, float]]:
    found = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else str(k)
            found.extend(_flatten_numbers(v, new_path))
        return found

    if isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            found.extend(_flatten_numbers(item, new_path))
        return found

    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        found.append((path, float(obj)))
        return found

    if isinstance(obj, str):
        cleaned = obj.replace(" ", "").replace(",", ".")
        if re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
            try:
                found.append((path, float(cleaned)))
            except Exception:
                pass
        else:
            m = re.search(r"(-?\d+(?:[.,]\d+)?)", obj)
            if m:
                try:
                    found.append((path, float(m.group(1).replace(",", "."))))
                except Exception:
                    pass
        return found

    return found


def _extract_candidate_value(data: Any, keywords: List[str]) -> Any:
    if isinstance(data, dict):
        for key, value in data.items():
            key_l = str(key).lower()
            if any(kw in key_l for kw in keywords):
                return value
            nested = _extract_candidate_value(value, keywords)
            if nested is not None:
                return nested

    elif isinstance(data, list):
        for item in data:
            nested = _extract_candidate_value(item, keywords)
            if nested is not None:
                return nested

    elif isinstance(data, str):
        txt = data.lower()
        if any(kw in txt for kw in keywords):
            return data

    return None


def _normalize_scalar(value: Any):
    if value is None:
        return None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value

    if isinstance(value, str):
        m = re.search(r"(-?\d+(?:[.,]\d+)?)", value.replace(" ", ""))
        if m:
            raw = m.group(1).replace(",", ".")
            try:
                num = float(raw)
                return int(num) if num.is_integer() else num
            except Exception:
                return value
        return value

    return value


def _guess_metrics(data_obj: Any) -> Dict[str, Any]:
    """
    Пытается вытащить факты из входных данных.
    Ничего не придумывает: если не нашёл — оставляет None.
    """
    metrics = {
        "budget_plan": None,
        "budget_fact": None,
        "volume_plan": None,
        "volume_fact": None,
        "payback_plan": None,
        "payback_fact": None,
        "project_name": None,
    }

    # Попытка найти проект
    project_name = _extract_candidate_value(data_obj, ["project", "проект", "name", "название"])
    if isinstance(project_name, str) and len(project_name) < 150:
        metrics["project_name"] = project_name.strip()

    # Бюджет
    budget_plan = _extract_candidate_value(data_obj, ["budget_plan", "план_бюджет", "бюджет_план", "план бюджет"])
    budget_fact = _extract_candidate_value(data_obj, ["budget_fact", "факт_бюджет", "бюджет_факт", "факт бюджет"])

    # Объём
    volume_plan = _extract_candidate_value(data_obj, ["volume_plan", "объем_план", "объём_план", "плановый объем", "плановый объём"])
    volume_fact = _extract_candidate_value(data_obj, ["volume_fact", "объем_факт", "объём_факт", "фактический объем", "фактический объём"])

    # Окупаемость
    payback_plan = _extract_candidate_value(data_obj, ["payback_plan", "окупаемость_план", "срок_окупаемости_план"])
    payback_fact = _extract_candidate_value(data_obj, ["payback_fact", "окупаемость_факт", "срок_окупаемости_факт"])

    metrics["budget_plan"] = _normalize_scalar(budget_plan)
    metrics["budget_fact"] = _normalize_scalar(budget_fact)
    metrics["volume_plan"] = _normalize_scalar(volume_plan)
    metrics["volume_fact"] = _normalize_scalar(volume_fact)
    metrics["payback_plan"] = _normalize_scalar(payback_plan)
    metrics["payback_fact"] = _normalize_scalar(payback_fact)

    return metrics


def _format_money(value: Any) -> str:
    if value is None:
        return "н/д"

    if isinstance(value, (int, float)):
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f} млн руб."
        return f"{value:,.0f} руб.".replace(",", " ")

    return str(value)


def _format_plain(value: Any, suffix: str = "") -> str:
    if value is None:
        return "н/д"
    return f"{value}{suffix}"


def _pct_delta(plan: Any, fact: Any):
    if not isinstance(plan, (int, float)) or not isinstance(fact, (int, float)):
        return None
    if plan == 0:
        return None
    return (fact - plan) / plan * 100


def _build_fact_pack(metrics: Dict[str, Any], waterfall_key: str) -> Dict[str, Any]:
    budget_delta = _pct_delta(metrics["budget_plan"], metrics["budget_fact"])
    volume_delta = _pct_delta(metrics["volume_plan"], metrics["volume_fact"])
    payback_delta = None

    if isinstance(metrics["payback_plan"], (int, float)) and isinstance(metrics["payback_fact"], (int, float)):
        payback_delta = metrics["payback_fact"] - metrics["payback_plan"]

    return {
        "project_name": metrics["project_name"],
        "budget_plan": metrics["budget_plan"],
        "budget_fact": metrics["budget_fact"],
        "budget_delta_pct": budget_delta,
        "volume_plan": metrics["volume_plan"],
        "volume_fact": metrics["volume_fact"],
        "volume_delta_pct": volume_delta,
        "payback_plan": metrics["payback_plan"],
        "payback_fact": metrics["payback_fact"],
        "payback_delta_years": payback_delta,
        "waterfall_key": waterfall_key or "не определён по данным",
    }


def _missing_fields(metrics: Dict[str, Any]) -> List[str]:
    missing = []
    for field, value in metrics.items():
        if field == "project_name":
            continue
        if value is None:
            missing.append(field)
    return missing


# =========================
# Main public function
# =========================
def generate_report_summary(inputs_data: Any, analysis: Dict[str, Any], waterfall_key: str = "") -> str:
    """
    Генерирует текст доклада только на основе входных данных.
    Ничего не придумывает. Если данных недостаточно, прямо сообщает об этом.
    """
    data_obj = _to_python_obj(inputs_data)
    metrics = _guess_metrics(data_obj)
    facts = _build_fact_pack(metrics, waterfall_key)
    missing = _missing_fields(metrics)

    # Если структурных метрик мало — не сочиняем, а честно пишем ограничение
    enough_core_data = any([
        facts["budget_plan"] is not None and facts["budget_fact"] is not None,
        facts["volume_plan"] is not None and facts["volume_fact"] is not None,
        facts["payback_plan"] is not None and facts["payback_fact"] is not None,
    ])

    if not enough_core_data:
        available_numbers = _flatten_numbers(data_obj)
        preview = available_numbers[:12]

        lines = [
            "Недостаточно структурированных данных для подготовки полноценного доклада.",
            "Я не буду додумывать отсутствующие показатели.",
            "",
            "Что желательно передать в файлах:",
            "- бюджет план / факт",
            "- объём производства план / факт",
            "- срок окупаемости план / факт",
            "- при наличии — ключевой фактор отклонений из водопада",
        ]

        if preview:
            lines.append("")
            lines.append("Числовые значения, которые удалось обнаружить во входных данных:")
            for path, value in preview:
                lines.append(f"- {path}: {value}")

        return "\n".join(lines)

    # Подготовка фактов для LLM
    fact_payload = {
        "project_name": facts["project_name"],
        "budget_plan": facts["budget_plan"],
        "budget_fact": facts["budget_fact"],
        "budget_delta_pct": facts["budget_delta_pct"],
        "volume_plan": facts["volume_plan"],
        "volume_fact": facts["volume_fact"],
        "volume_delta_pct": facts["volume_delta_pct"],
        "payback_plan": facts["payback_plan"],
        "payback_fact": facts["payback_fact"],
        "payback_delta_years": facts["payback_delta_years"],
        "waterfall_key": facts["waterfall_key"],
        "analysis_plan": analysis,
        "missing_fields": missing,
    }

    prompt = f"""
Ты готовишь короткий доклад финансового аналитика на русском языке.

Жёсткие правила:
1. Используй только факты из FACTS_JSON ниже.
2. Нельзя придумывать цифры, проценты, сроки, причины и выводы, которых нет в фактах.
3. Если каких-то данных не хватает, прямо так и напиши.
4. Стиль: деловой, логичный, без канцелярита, 2-4 абзаца.
5. Если есть waterfall_key, упомяни его как ключевой фактор влияния.
6. Не добавляй никаких вводных фраз про ИИ, модель, предположения или "возможно".
7. Не используй markdown-таблицы.
8. Если названия проекта нет, не выдумывай его.

FACTS_JSON:
{json.dumps(fact_payload, ensure_ascii=False, indent=2)}
"""

    try:
        response = llm_humanizer.invoke(prompt)
        text = response.content.strip()

        # Минимальный пост-фильтр от явной галлюцинации:
        # если текст слишком пустой — даём deterministic fallback.
        if not text:
            raise ValueError("Empty LLM response")

        return text

    except Exception:
        # Fallback без LLM — только факты.
        project_prefix = ""
        if facts["project_name"]:
            project_prefix = f"По проекту «{facts['project_name']}» "

        parts = []

        p1 = (
            f"{project_prefix}исходные параметры составляли: "
            f"бюджет — {_format_money(facts['budget_plan'])}, "
            f"объём — {_format_plain(facts['volume_plan'])}, "
            f"срок окупаемости — {_format_plain(facts['payback_plan'], ' года')}."
        )
        parts.append(p1)

        p2 = (
            f"Фактические показатели составили: "
            f"бюджет — {_format_money(facts['budget_fact'])}, "
            f"объём — {_format_plain(facts['volume_fact'])}, "
            f"срок окупаемости — {_format_plain(facts['payback_fact'], ' года')}."
        )
        parts.append(p2)

        deviations = []
        if facts["budget_delta_pct"] is not None:
            deviations.append(f"бюджет изменился на {facts['budget_delta_pct']:.1f}%")
        if facts["volume_delta_pct"] is not None:
            deviations.append(f"объём изменился на {facts['volume_delta_pct']:.1f}%")
        if facts["payback_delta_years"] is not None:
            deviations.append(f"срок окупаемости изменился на {facts['payback_delta_years']:.1f} года")

        if deviations:
            parts.append("Основные отклонения: " + "; ".join(deviations) + ".")

        if facts["waterfall_key"]:
            parts.append(f"По данным факторного анализа ключевое влияние оказал фактор: {facts['waterfall_key']}.")

        if missing:
            human_missing = ", ".join(missing)
            parts.append(f"Часть показателей отсутствует во входных данных: {human_missing}.")

        return "\n\n".join(parts)