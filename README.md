# FinCopilot

Локальный ReAct-агент для финансового аналитика с UI на Streamlit и локальной LLM через Ollama.

Проект предназначен для анализа CapEx, смет, план/факт, факторных отклонений, ликвидности, себестоимости и подготовки Excel-отчётов на основе загруженных файлов Excel/PDF.

## Возможности

- Локальная работа через Ollama без облачных API
- UI на Streamlit
- Загрузка Excel и PDF-файлов
- Анализ сметы и план/факт
- Факторный анализ отклонений
- Подготовка текста доклада
- Выгрузка результатов в чистый Excel (`.xlsx`)
- Защита от галлюцинаций: агент не должен придумывать цифры, если данных нет

## Стек

- Python
- Streamlit
- Ollama
- LangChain
- LangGraph
- Pandas
- OpenPyXL
- PDFPlumber

## Структура проекта

```text
.
├── README.md
├── app.py
├── config.yaml
├── main.py
├── requirements.txt
├── inputs/
├── outputs/
├── assets/
└── tools
    ├── document_parser.py
    ├── excel_report.py
    └── report_generator.py
```

## Требования

Перед запуском должны быть установлены:

- Python 3.10+
- Ollama
- локально загруженная модель `qwen2.5:7b-instruct-q5_K_M`

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ZaitsevaYG/FinCopilot.git
cd FinCopilot
```

### 2. Создать виртуальное окружение

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Установить зависимости

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Установить и запустить Ollama

Установите Ollama с официального сайта:
[https://ollama.com/download](https://ollama.com/download)

Проверьте, что Ollama установлен:

```bash
ollama --version
```

Запустите сервер Ollama, если он не стартует автоматически:

```bash
ollama serve
```

### 5. Загрузить модель

```bash
ollama pull qwen2.5:7b-instruct-q5_K_M
```

### 6. Проверить конфиг

Файл `config.yaml` должен содержать:

```yaml
model: "qwen2.5:7b-instruct-q5_K_M"
ollama_base: "http://localhost:11434"
output_dir: "outputs"

temperature:
  router: 0.1
  analyst: 0.1
  writer: 0.3

triggers:
  - "проанализируй смету"
  - "анализ сметы"
  - "факторный анализ"
  - "анализ отклонений"
  - "план/факт"
  - "план факт"
  - "ликвидность"
  - "себестоимость"
  - "диаграмма-водопад"
  - "водопад"
  - "доклад"
  - "текст доклада"
  - "резюме"
  - "полный анализ"
  - "составь таблицу"
  - "сравнительная таблица"
```

## Запуск приложения

```bash
streamlit run app.py
```

После запуска откроется локальный веб-интерфейс Streamlit.

Обычно Streamlit поднимает приложение на адресе:

[http://localhost:8501](http://localhost:8501)

## Как использовать

1. Откройте приложение в браузере.
2. В боковой панели загрузите входные файлы:
   - Excel (`.xlsx`, `.xls`, `.xlsm`)
   - PDF (`.pdf`)
3. Введите запрос в чат.
4. Дождитесь завершения анализа.
5. Скачайте итоговый Excel-отчёт.

## Примеры запросов

- `Проанализируй смету`
- `Составь сравнительную таблицу план/факт`
- `Сделай факторный анализ отклонений`
- `Построй диаграмму-водопад отклонений`
- `Подготовь текст доклада по данным проекта`
- `Сделай полный анализ проекта`

## Логика работы

### `app.py`
UI на Streamlit:
- загрузка файлов
- чат
- запуск аналитики
- скачивание Excel-отчёта

### `main.py`
Основной оркестратор:
- читает `config.yaml`
- запускает парсер входных файлов
- маршрутизирует запрос
- вызывает ReAct-агента
- формирует Excel и текст доклада

### `tools/document_parser.py`
Парсер входных файлов:
- читает Excel и PDF
- извлекает таблицы, текст и ключевые метрики
- возвращает единый JSON-слепок данных

### `tools/excel_report.py`
Формирование Excel-отчёта:
- summary
- plan_fact
- factor_analysis
- liquidity
- costing
- waterfall_data
- raw_metrics
- source_files
- numeric_hints

### `tools/report_generator.py`
Генерация текстового доклада:
- строит краткое резюме по данным
- не должен придумывать отсутствующие значения

## Важные ограничения

- Агент работает только по загруженным данным
- Если нужных цифр нет, агент должен запросить уточнение или сообщить о нехватке данных
- Результат анализа должен сохраняться в Excel
- PDF-сканы без текстового слоя могут парситься плохо без OCR
- Для лучшего качества отчёта желательно загружать структурированные Excel-файлы

## Рекомендуемая структура входных данных

Желательно, чтобы во входных таблицах присутствовали поля или близкие по смыслу названия:

- `budget_plan`
- `budget_fact`
- `volume_plan`
- `volume_fact`
- `payback_plan`
- `payback_fact`
- `project_name`

Допустимы и русские аналоги:
- бюджет план / бюджет факт
- объём план / объём факт
- срок окупаемости план / факт
- проект / название проекта

## Возможные ошибки

### 1. `Ollama connection error`
Проверьте, что Ollama запущен:

```bash
ollama serve
```

### 2. `model not found`
Проверьте, что модель загружена:

```bash
ollama pull qwen2.5:7b-instruct-q5_K_M
```

### 3. `No module named ...`
Переустановите зависимости:

```bash
pip install -r requirements.txt
```

### 4. Не формируется Excel
Проверьте:
- существует ли папка `outputs`
- есть ли права на запись
- корректны ли входные данные
- установлены ли `pandas` и `openpyxl`

### 5. PDF почти не извлекается
Вероятно, PDF является сканом без текстового слоя. В таком случае нужен OCR или исходный Excel.

## requirements.txt

Рекомендуемый вариант:

```txt
streamlit>=1.44.0
pandas>=2.2.0
openpyxl>=3.1.2
pdfplumber>=0.11.0
python-dotenv>=1.0.1
PyYAML>=6.0.1
langchain>=0.3.0
langchain-core>=0.3.0
langgraph>=0.2.0
langchain-ollama>=0.2.0
pydantic>=2.7.0
```

## Пример локального запуска

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct-q5_K_M
streamlit run app.py
```

## Дальнейшее развитие

- OCR для сканированных PDF
- более точный факторный анализ по структуре сметы
- настройка шаблонов Excel под корпоративный формат
- расширение набора финансовых метрик
- улучшение маршрутизации задач агента

## Лицензия

Используйте и дорабатывайте проект в соответствии с вашей внутренней политикой или лицензией репозитория.