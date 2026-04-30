from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, Reference
from pathlib import Path
import json

def generate_capex_excel(query: str, inputs_data: dict, agent_plan: dict):
    """Генерирует Excel по плану агента: полный или отдельный лист/диаграмма"""
    wb = Workbook()
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Общие стили
    header_font = Font(bold=True, size=14)
    title_font = Font(bold=True, size=16)
    green_fill = PatternFill(start_color="90EE90", fill_type="solid")
    red_fill = PatternFill(start_color="FFB6C1", fill_type="solid")
    
    if agent_plan.get("full_report", False) or "полный" in query.lower():
        # Все листы
        ws_smeta = create_smeta_sheet(wb.active, inputs_data)
        create_factor_sheet(wb.create_sheet("Факторный_Анализ"), inputs_data)
        create_planfact_sheet(wb.create_sheet("План_Факт"), inputs_data)
        create_liquidity_sheet(wb.create_sheet("Ликвидность"), inputs_data)
        create_costing_sheet(wb.create_sheet("Себестоимость"), inputs_data)
        create_waterfall_sheet(wb.create_sheet("Водопад_Отклонения"), inputs_data)
        
    else:
        # Только нужный лист
        intent = agent_plan.get("intent", "smeta")
        if intent == "variance_factor":
            create_factor_sheet(wb.active, inputs_data)
        elif intent == "plan_fact":
            create_planfact_sheet(wb.active, inputs_data)
        elif intent == "liquidity":
            create_liquidity_sheet(wb.active, inputs_data)
        elif intent == "costing":
            create_costing_sheet(wb.active, inputs_data)
        elif intent == "waterfall":
            create_waterfall_sheet(wb.active, inputs_data)
        else:
            create_smeta_sheet(wb.active, inputs_data)
    
    filename = f"capex_{agent_plan.get('sheet_name', 'report')}.xlsx"
    filepath = output_dir / filename
    wb.save(filepath)
    return str(filepath)

def create_smeta_sheet(ws, data):
    ws.title = "Смета"
    ws['A1'] = "📊 Анализ сметы"; ws['A1'].font = Font(bold=True, size=16)
    headers = ["Статья", "План RUB", "Факт RUB", "Откл RUB", "Откл %"]
    for c, h in enumerate(headers, 1):
        ws.cell(row=3, column=c, value=h).font = Font(bold=True)
    
    # Демо-данные (заменить на реальные из inputs_data)
    rows = [
        ["Материалы", 1000000, 1100000, "=C4-B4", "=IF(B4=0,0,D4/B4)"],
        ["Зарплата", 500000, 450000, "=C5-B5", "=IF(B5=0,0,D5/B5)"],
        ["Overhead", 300000, 320000, "=C6-B6", "=IF(B6=0,0,D6/B6)"],
        ["ИТОГО", "=SUM(B4:B6)", "=SUM(C4:C6)", "=D7-B7", "=IF(B7=0,0,D7/B7)"]
    ]
    for row in rows:
        ws.append(row)
    return ws

def create_factor_sheet(ws, data):
    ws['A1'] = "🔍 Факторный анализ"; ws['A1'].font = Font(bold=True, size=16)
    ws['A3'] = "Фактор"; ws['B3'] = "План"; ws['C3'] = "Факт1"; ws['D3'] = "Факт2"; ws['E3'] = "Откл"
    ws.append(["Объём", 1000, 1000, 1100, "=D4*C5-B4*C5"])
    ws.append(["Цена", 1000, 1050, 1050, "=D5*D4-C5*D4"])
    ws.append(["Итого", "=B4*B6", "=C4*C6", "=D4*D6", "=E7-B7"])
    return ws

def create_planfact_sheet(ws, data):
    ws['A1'] = "📈 План/Факт"; ws['A1'].font = Font(bold=True, size=16)
    ws['A3'] = "Месяц"; ws['B3'] = "План"; ws['C3'] = "Факт"; ws['D3'] = "Откл%"
    for i in range(1, 13):
        row = i + 3
        ws.append([f"М{i}", 100000 * i, 105000 * i, f"=IF(B{row}=0,0,(C{row}-B{row})/B{row})"])
    return ws

def create_liquidity_sheet(ws, data):
    ws['A1'] = "💧 Ликвидность проекта"; ws['A1'].font = Font(bold=True, size=16)
    ws['A3'] = "Показатель"; ws['B3'] = "Значение"; ws['C3'] = "Норма"
    ws.append(["Текущая ликвидность", 1.8, ">1.5"])
    ws.append(["Быстрая", 1.2, ">0.8"])
    ws.append(["Абсолютная", 0.4, ">0.2"])
    return ws

def create_costing_sheet(ws, data):
    ws['A1'] = "💰 Расчёт себестоимости"; ws['A1'].font = Font(bold=True, size=16)
    ws['A3'] = "Параметр"; ws['B3'] = "Значение"; ws['C3'] = "Формула"
    ws.append(["Материалы/ед", 500, "Объём * Цена"])
    ws.append(["ЗП/ед", 200, "=B4 * 0.4"])
    ws.append(["Overhead/ед", 100, "=B5 * 0.2"])
    ws.append(["Себестоимость", "=SUM(B4:B6)", "Итого/ед"])
    return ws

def create_waterfall_sheet(ws, data):
    ws['A1'] = "📉 Водопад отклонений"; ws['A1'].font = Font(bold=True, size=16)
    ws['A3'] = "Категория"; ws['B3'] = "План"; ws['C3'] = "Факт"; ws['D3'] = "Откл"
    ws.append(["Начало", 0, 0, 0])
    ws.append(["Материалы", 1000000, 1100000, 100000])
    ws.append(["Зарплата", 500000, 450000, -50000])
    ws.append(["Overhead", 300000, 320000, 20000])
    ws.append(["Итого", "=SUM(B2:B5)", "=SUM(C2:C5)", "=SUM(D2:D5)"])
    
    # Диаграмма водопад
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.title = "Отклонения по статьям"
    data_ref = Reference(ws, min_col=2, min_row=1, max_row=6, max_col=4)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=6)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, "F2")
    return ws