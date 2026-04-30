from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
from openpyxl.chart import BarChart, Reference
from pathlib import Path
import os

def generate_capex_excel_full(query, inputs_data, agent_result):
    """Полный отчёт со всеми задачами"""
    wb = Workbook()
    
    # СМЕТА + ОТКЛОНЕНИЯ
    ws_smeta = wb.active
    ws_smeta.title = "Смета_Анализ"
    ws_smeta['A1'] = "📊 Анализ сметы"; ws_smeta['A1'].font = Font(bold=True, size=16)
    ws_smeta['A3'] = "Статья"; ws_smeta['B3'] = "План RUB"; ws_smeta['C3'] = "Факт RUB"; ws_smeta['D3'] = "Откл RUB"; ws_smeta['E3'] = "Откл %"
    data_smeta = [
        ["Материалы", 1000000, 1100000, "=C4-B4", "=IF(B4=0,0,D4/B4)"],
        ["Зарплата", 500000, 450000, "=C5-B5", "=IF(B5=0,0,D5/B5)"],
        ["Overhead", 300000, 320000, "=C6-B6", "=IF(B6=0,0,D6/B6)"],
        ["ИТОГО", "=SUM(B4:B6)", "=SUM(C4:C6)", "=D7-B7", "=IF(B7=0,0,D7/B7)"]
    ]
    for row in data_smeta:
        ws_smeta.append(row)
    # Conditional Formatting
    green = PatternFill(start_color="90EE90", fill_type="solid")
    red = PatternFill(start_color="FFB6C1", fill_type="solid")
    
    # ФАКТОРНЫЙ АНАЛИЗ
    ws_factor = wb.create_sheet("Факторный_Анализ")
    ws_factor['A1'] = "🔍 Факторный анализ отклонений"; ws_factor['A1'].font = Font(bold=True, size=16)
    ws_factor['A3'] = "Фактор"; ws_factor['B3'] = "План"; ws_factor['C3'] = "Факт1"; ws_factor['D3'] = "Факт2"; ws_factor['E3'] = "Откл"
    ws_factor.append(["Объём", 1000, 1000, 1100, "=D4*C5-B4*C5"])
    ws_factor.append(["Цена", 1000, 1050, 1050, "=D5*D4-C5*D4"])
    ws_factor.append(["Итого", "=B4*B6", "=C4*C6", "=D4*D6", "=E7-B7"])
    
    # ПЛАН/ФАКТ
    ws_planfact = wb.create_sheet("План_Факт")
    ws_planfact['A1'] = "📈 План/Факт сравнение"
    ws_planfact['A3'] = "Месяц"; ws_planfact['B3'] = "План"; ws_planfact['C3'] = "Факт"; ws_planfact['D3'] = "Откл%"
    for i in range(1, 13):
        ws_planfact.append([f"М{i}", 100000, 105000, "=IF(B{0}=0,0,(C{0}-B{0})/B{0})".format(i+3)])
    
    # ЛИКВИДНОСТЬ
    ws_liq =