import os
from pathlib import Path
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage
from tools.document_parser import parse_inputs
from tools.excel_report import generate_capex_excel
import yaml
import argparse

load_dotenv()
with open("config.yaml") as f:
    config = yaml.safe_load(f)

llm = OllamaLLM(model=config["model"], base_url=config["ollama_base"])

# ReAct инструменты
tools = [
    parse_inputs,  # Читает inputs/
    lambda x: "Мок-инструмент цен: инфляция 8%, мебель +15%",  # Placeholder
]

agent = create_react_agent(llm, tools)


def run_capex_agent(query: str):
    """ReAct: разбивает задачу → Excel"""
    if any(t in query.lower() for t in config["triggers"]):
        print("🚀 ReAct агент запущен...")

        # Этап 1: Сбор данных
        inputs_data = parse_inputs(query)

        # Этап 2: ReAct анализ
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(content=f"CapEx {query}. Данные: {inputs_data}")
                ]
            }
        )

        # Этап 3: ВЫХОД ТОЛЬКО EXCEL
        output_path = generate_capex_excel(query, inputs_data, result)
        print(f"✅ Отчёт: {output_path}")
        return output_path
    return "Триггер не найден"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="Запрос с триггером")
    args = parser.parse_args()
    run_capex_agent(args.query)
