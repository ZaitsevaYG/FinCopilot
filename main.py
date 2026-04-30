import os
from pathlib import Path
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from tools.document_parser import parse_inputs
from tools.excel_report import generate_capex_excel
import yaml
import argparse
import json

load_dotenv()
with open("config.yaml") as f:
    config = yaml.safe_load(f)

# ChatOllama вместо OllamaLLM для structured output
llm = ChatOllama(model=config["model"], base_url=config["ollama_base"], temperature=0.1)

class TaskPlan(BaseModel):
    """План задач для Excel"""
    intent: str = Field(description="variance_factor|plan_fact|liquidity|costing|waterfall|smeta")
    full_report: bool = Field(default=False, description="Нужен полный Excel?")
    sheet_name: str = Field(default="report", description="Имя листа для файла")

tools = [parse_inputs]

agent = create_react_agent(llm, tools)

def run_capex_agent(query: str):
    """ReAct: парсит намерение → Excel"""
    triggers = config["triggers"]
    if any(t in query.lower() for t in triggers):
        print("🚀 ReAct агент запущен...")
        
        # Router: разбираем намерение
        router_prompt = f"""
        Определи задачу по запросу: "{query}"
        Верни JSON с intent (один из: smeta, variance_factor, plan_fact, liquidity, costing, waterfall), 
        full_report (true если "полный" или все задачи), sheet_name.
        """
        plan = llm.invoke(router_prompt).content
        try:
            agent_plan = json.loads(plan)
        except:
            agent_plan = {"intent": "smeta", "full_report": False}
        
        # Этап 1: данные
        inputs_data = parse_inputs(query)
        
        # Этап 2: ReAct (доп.анализ)
        result = agent.invoke({
            "messages": [HumanMessage(content=f"Анализ для {query}. Данные: {inputs_data}")]
        })
        
        # Этап 3: Excel
        output_path = generate_capex_excel(query, inputs_data, agent_plan)
        print(f"✅ {output_path}")
        return output_path
    return "outputs/default_report.xlsx"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str)
    args = parser.parse_args()
    run_capex_agent(args.query)