import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pdfplumber


# =========================
# Constants
# =========================
INPUTS_DIR = Path("inputs")
SUPPORTED_EXCEL = {".xlsx", ".xls", ".xlsm"}
SUPPORTED_PDF = {".pdf"}


# =========================
# Text normalization
# =========================
def _norm_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _norm_key(value: Any) -> str:
    text = _norm_text(value).lower()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sanitize_cell(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    return value


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    text = _norm_text(value)
    if not text:
        return None

    text = text.replace("\xa0", " ")
    text = text.replace("%", "")
    text = text.replace("₽", "").replace("руб.", "").replace("руб", "")
    text = text.replace("млн", "").replace("тыс", "")
    text = text.strip()

    text_no_space = text.replace(" ", "")

    # 1 234,56 / 1234.56 / -1234
    match = re.search(r"-?\d[\d\s]*[.,]?\d*", text_no_space)
    if not match:
        return None

    raw = match.group(0).replace(" ", "")
    if raw.count(",") > 0 and raw.count(".") == 0:
        raw = raw.replace(",", ".")
    elif raw.count(",") > 0 and raw.count(".") > 0:
        raw = raw.replace(" ", "").replace(",", "")

    try:
        return float(raw)
    except Exception:
        return None


def _looks_like_header_row(row: List[Any]) -> bool:
    non_empty = [x for x in row if _norm_text(x)]
    if not non_empty:
        return False

    text_cells = sum(1 for x in non_empty if isinstance(x, str))
    return text_cells >= max(1, len(non_empty) // 2)


# =========================
# Metric aliases
# =========================
METRIC_ALIASES = {
    "budget_plan": [
        "budget_plan", "бюджет план", "план бюджет", "плановый бюджет", "бюджет_план",
        "capex plan", "investment plan", "инвестиции план", "смета план", "план сметы"
    ],
    "budget_fact": [
        "budget_fact", "бюджет факт", "факт бюджет", "фактический бюджет", "бюджет_факт",
        "capex fact", "investment fact", "инвестиции факт", "смета факт", "факт сметы"
    ],
    "volume_plan": [
        "volume_plan", "объем план", "объём план", "плановый объем", "плановый объём",
        "выпуск план", "production plan", "output plan"
    ],
    "volume_fact": [
        "volume_fact", "объем факт", "объём факт", "фактический объем", "фактический объём",
        "выпуск факт", "production fact", "output fact"
    ],
    "payback_plan": [
        "payback_plan", "окупаемость план", "срок окупаемости план", "план окупаемости",
        "payback period plan", "irr plan", "npv plan"
    ],
    "payback_fact": [
        "payback_fact", "окупаемость факт", "срок окупаемости факт", "факт окупаемости",
        "payback period fact", "irr fact", "npv fact"
    ],
    "project_name": [
        "project", "project name", "название проекта", "проект", "наименование проекта"
    ],
}


# =========================
# Matching helpers
# =========================
def _contains_alias(text: str, aliases: List[str]) -> bool:
    t = _norm_key(text)
    return any(alias in t for alias in aliases)


def _assign_metric_if_match(metrics: Dict[str, Any], key_text: str, candidate_value: Any) -> bool:
    key_norm = _norm_key(key_text)

    for metric_name, aliases in METRIC_ALIASES.items():
        if _contains_alias(key_norm, aliases):
            if metric_name == "project_name":
                if candidate_value is not None and not metrics.get(metric_name):
                    metrics[metric_name] = _norm_text(candidate_value)
                    return True
            else:
                parsed = _parse_number(candidate_value)
                if parsed is not None and metrics.get(metric_name) is None:
                    metrics[metric_name] = parsed
                    return True
    return False


def _scan_key_value_pairs(records: List[Tuple[str, Any]], metrics: Dict[str, Any]):
    for key_text, value in records:
        _assign_metric_if_match(metrics, key_text, value)


# =========================
# Excel parsing
# =========================
def _read_excel_file(file_path: Path) -> Dict[str, Any]:
    result = {
        "file_name": file_path.name,
        "file_type": "excel",
        "sheets": {},
        "text_fragments": [],
        "metrics_found": {},
        "tables_preview": {},
    }

    metrics = {
        "budget_plan": None,
        "budget_fact": None,
        "volume_plan": None,
        "volume_fact": None,
        "payback_plan": None,
        "payback_fact": None,
        "project_name": None,
    }

    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        result["error"] = f"excel_open_error: {e}"
        return result

    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        except Exception as e:
            result["sheets"][sheet_name] = {"error": f"sheet_read_error: {e}"}
            continue

        df = df.applymap(_sanitize_cell)
        rows = df.values.tolist()

        preview_rows = []
        kv_candidates = []

        for i, row in enumerate(rows):
            clean_row = [_sanitize_cell(x) for x in row]
            non_empty = [x for x in clean_row if x is not None]

            if not non_empty:
                continue

            row_text = " | ".join(_norm_text(x) for x in non_empty[:10])
            if row_text:
                result["text_fragments"].append(f"[{sheet_name}] {row_text}")

            preview_rows.append([_norm_text(x) for x in clean_row[:12]])

            # Сценарий 1: строка вида "Показатель | Значение"
            if len(non_empty) >= 2:
                key_candidate = non_empty[0]
                value_candidate = non_empty[1]
                kv_candidates.append((_norm_text(key_candidate), value_candidate))

            # Сценарий 2: заголовочная строка + следующая строка со значениями
            if i < len(rows) - 1 and _looks_like_header_row([x for x in clean_row if x is not None]):
                next_row = rows[i + 1]
                if next_row:
                    for col_idx, header_cell in enumerate(clean_row):
                        if header_cell is None:
                            continue
                        if col_idx < len(next_row):
                            value_candidate = next_row[col_idx]
                            kv_candidates.append((_norm_text(header_cell), value_candidate))

            # Сценарий 3: парный проход по соседним ячейкам в строке
            for j in range(len(clean_row) - 1):
                left = clean_row[j]
                right = clean_row[j + 1]
                if left is not None and right is not None:
                    kv_candidates.append((_norm_text(left), right))

        _scan_key_value_pairs(kv_candidates, metrics)

        result["sheets"][sheet_name] = {
            "rows": int(len(rows)),
            "cols": int(df.shape[1]) if not df.empty else 0,
            "preview": preview_rows[:20],
        }
        result["tables_preview"][sheet_name] = preview_rows[:10]

    result["metrics_found"] = metrics
    return result


# =========================
# PDF parsing
# =========================
def _extract_pdf_tables(page) -> List[List[List[str]]]:
    extracted_tables = []
    try:
        tables = page.extract_tables() or []
        for table in tables:
            if not table:
                continue
            clean_table = []
            for row in table:
                if row is None:
                    continue
                clean_table.append([_norm_text(cell) for cell in row])
            if clean_table:
                extracted_tables.append(clean_table)
    except Exception:
        pass
    return extracted_tables


def _read_pdf_file(file_path: Path) -> Dict[str, Any]:
    result = {
        "file_name": file_path.name,
        "file_type": "pdf",
        "pages": [],
        "text_fragments": [],
        "metrics_found": {},
        "tables_preview": [],
    }

    metrics = {
        "budget_plan": None,
        "budget_fact": None,
        "volume_plan": None,
        "volume_fact": None,
        "payback_plan": None,
        "payback_fact": None,
        "project_name": None,
    }

    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                page_text = page_text.strip()

                page_entry = {
                    "page": page_num,
                    "text_preview": page_text[:3000],
                    "tables": [],
                }

                if page_text:
                    result["text_fragments"].append(f"[page {page_num}] {page_text[:1000]}")

                    # Поиск строк "ключ: значение"
                    for line in page_text.splitlines():
                        line_clean = line.strip()
                        if not line_clean:
                            continue

                        if ":" in line_clean:
                            left, right = line_clean.split(":", 1)
                            _assign_metric_if_match(metrics, left, right)

                        # Поиск паттерна "... план ..." / "... факт ..."
                        for metric_name, aliases in METRIC_ALIASES.items():
                            for alias in aliases:
                                if alias in _norm_key(line_clean):
                                    number = _parse_number(line_clean)
                                    if metric_name == "project_name":
                                        if metrics["project_name"] is None:
                                            metrics["project_name"] = line_clean
                                    elif number is not None and metrics.get(metric_name) is None:
                                        metrics[metric_name] = number

                tables = _extract_pdf_tables(page)
                if tables:
                    page_entry["tables"] = tables[:5]
                    for table in tables:
                        result["tables_preview"].append(table[:10])

                        # Вытащим пары ключ-значение из таблиц
                        for row in table:
                            row_non_empty = [cell for cell in row if _norm_text(cell)]
                            if len(row_non_empty) >= 2:
                                _assign_metric_if_match(metrics, row_non_empty[0], row_non_empty[1])

                            # header-value pattern
                            if _looks_like_header_row(row_non_empty):
                                for idx in range(len(row_non_empty) - 1):
                                    _assign_metric_if_match(metrics, row_non_empty[idx], row_non_empty[idx + 1])

                result["pages"].append(page_entry)

    except Exception as e:
        result["error"] = f"pdf_open_error: {e}"
        return result

    result["metrics_found"] = metrics
    return result


# =========================
# Merge metrics
# =========================
def _merge_metric_dicts(all_metric_dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged = {
        "budget_plan": None,
        "budget_fact": None,
        "volume_plan": None,
        "volume_fact": None,
        "payback_plan": None,
        "payback_fact": None,
        "project_name": None,
    }

    for metric_dict in all_metric_dicts:
        for key, value in metric_dict.items():
            if merged.get(key) is None and value is not None:
                merged[key] = value

    return merged


def _collect_numeric_hints(parsed_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hints = []

    def walk(obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:100]):
                walk(item, f"{path}[{i}]")
        else:
            num = _parse_number(obj)
            if num is not None:
                hints.append({"path": path, "value": num})

    for pf in parsed_files:
        walk(pf)

    unique = []
    seen = set()
    for item in hints:
        key = (item["path"], item["value"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:200]


# =========================
# Public parser
# =========================
def parse_inputs(query: str = "") -> str:
    """
    Читает inputs/*.xlsx|xls|xlsm|pdf и возвращает единый JSON-слепок данных.
    Возвращает строку JSON, чтобы downstream-модули могли безопасно его сериализовать.
    """
    if not INPUTS_DIR.exists():
        return json.dumps(
            {
                "status": "error",
                "message": "Папка inputs не найдена",
                "query": query,
                "files": [],
                "metrics": {},
            },
            ensure_ascii=False,
            indent=2,
        )

    files = [p for p in INPUTS_DIR.iterdir() if p.is_file()]
    files = sorted(files, key=lambda x: x.name.lower())

    if not files:
        return json.dumps(
            {
                "status": "error",
                "message": "В папке inputs нет файлов",
                "query": query,
                "files": [],
                "metrics": {},
            },
            ensure_ascii=False,
            indent=2,
        )

    parsed_files = []
    metric_dicts = []

    for file_path in files:
        suffix = file_path.suffix.lower()

        if suffix in SUPPORTED_EXCEL:
            parsed = _read_excel_file(file_path)
            parsed_files.append(parsed)
            metric_dicts.append(parsed.get("metrics_found", {}))

        elif suffix in SUPPORTED_PDF:
            parsed = _read_pdf_file(file_path)
            parsed_files.append(parsed)
            metric_dicts.append(parsed.get("metrics_found", {}))

        else:
            parsed_files.append({
                "file_name": file_path.name,
                "file_type": "unsupported",
                "warning": f"Неподдерживаемый формат: {suffix}",
            })

    merged_metrics = _merge_metric_dicts(metric_dicts)
    numeric_hints = _collect_numeric_hints(parsed_files)

    result = {
        "status": "ok",
        "query": query,
        "files_count": len(parsed_files),
        "files": parsed_files,
        "metrics": merged_metrics,
        "numeric_hints": numeric_hints,
        "parser_notes": {
            "supported_formats": ["xlsx", "xls", "xlsm", "pdf"],
            "logic": [
                "поиск ключевых метрик в Excel по строкам, столбцам и header-value шаблонам",
                "поиск ключевых метрик в PDF по тексту, строкам вида 'ключ: значение' и таблицам",
                "агрегация первой найденной непустой метрики по всем файлам",
            ],
            "guardrail": "парсер не выдумывает значения, а возвращает только найденные факты",
        },
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# =========================
# Optional local debug
# =========================
if __name__ == "__main__":
    print(parse_inputs("тестовый запрос"))