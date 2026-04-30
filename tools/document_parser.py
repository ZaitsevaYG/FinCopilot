from langchain.tools import tool
import openpyxl
import pdfplumber
from pathlib import Path


@tool
def parse_inputs(query: str):
    """Парсит все Excel/PDF из inputs/"""
    data = {}
    for file in Path("inputs").glob("*"):
        if file.suffix == ".xlsx":
            wb = openpyxl.load_workbook(file)
            data[str(file)] = (
                f"Итого: {sum(cell.value or 0 for row in wb.active.iter_rows(values_only=True))}"
            )
        elif file.suffix == ".pdf":
            with pdfplumber.open(file) as pdf:
                data[str(file)] = pdf.pages[0].extract_text()[:500]
    return data
