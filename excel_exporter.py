import pandas as pd
import io
import re
from openpyxl.utils import get_column_letter

from inspector_logs.core import format_inspection_export_dataframe

def parse_top5_string(data_str):
    """문자열 형태의 Top5 데이터를 리스트로 변환 (예: 'proc1:100MB | proc2:50MB')"""
    if not data_str or str(data_str).lower() in ["no_active_io", "nan", "none"]:
        return []
    
    items = []
    for item in [x.strip() for x in str(data_str).split('|') if x.strip()]:
        if ':' in item:
            name, val = item.split(':', 1)
            items.append((name.strip(), val.strip()))
    return items

def generate_excel(df, selected_cols):
    """
    selected_cols 및 프로세스 데이터를 포함하여 엑셀 파일을 생성합니다.
    """
    output = io.BytesIO()
    
    # 1. 시계열 지표 데이터 준비
    export_df = df[['Timestamp'] + selected_cols].copy()
    
    # 2. 프로세스 데이터 추가 (데이터가 존재하는 경우)
    # 메모리 프로세스
    if 'Top5_Memory_MB' in df.columns:
        for i in range(5):
            export_df[f'Top_Mem_Proc_{i+1}'] = df['Top5_Memory_MB'].apply(
                lambda x: parse_top5_string(x)[i][0] if len(parse_top5_string(x)) > i else ""
            )
            export_df[f'Top_Mem_Val_{i+1}'] = df['Top5_Memory_MB'].apply(
                lambda x: parse_top5_string(x)[i][1] if len(parse_top5_string(x)) > i else ""
            )

    # 디스크 프로세스
    if 'Top5_Disk_IO_Global(MB/s)' in df.columns:
        for i in range(5):
            export_df[f'Top_Disk_Proc_{i+1}'] = df['Top5_Disk_IO_Global(MB/s)'].apply(
                lambda x: parse_top5_string(x)[i][0] if len(parse_top5_string(x)) > i else ""
            )
            export_df[f'Top_Disk_Val_{i+1}'] = df['Top5_Disk_IO_Global(MB/s)'].apply(
                lambda x: parse_top5_string(x)[i][1] if len(parse_top5_string(x)) > i else ""
            )
    
    # 컬럼 순서 조정 (Timestamp를 '값'으로 표시하거나 유지)
    export_df.rename(columns={'Timestamp': '시간(Timestamp)'}, inplace=True)
    
    def sanitize_str(val):
        if isinstance(val, str):
            # Remove control characters except \n, \t, \r
            return ''.join(c for c in val if ord(c) >= 32 or ord(c) in (9, 10, 13))
        return val

    # Sanitize dataframe columns and string data
    export_df.columns = [sanitize_str(c) for c in export_df.columns]
    for col in export_df.select_dtypes(include=['object']):
        export_df[col] = export_df[col].apply(sanitize_str)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='System_Resource_Report')
        
    return output.getvalue()


def _apply_column_widths(writer, sheet_name, export_df):
    worksheet = writer.book[sheet_name]
    for column_index, column_name in enumerate(export_df.columns, start=1):
        column_values = [column_name, *export_df[column_name].astype(str).tolist()]
        max_length = min(max(len(str(value)) for value in column_values) + 2, 28)
        worksheet.column_dimensions[get_column_letter(column_index)].width = max_length


def generate_inspection_excel(inspection_records):
    """
    검사 결과 레코드를 XLSX로 내보냅니다.
    """
    output = io.BytesIO()
    export_df = format_inspection_export_dataframe(inspection_records)

    with pd.ExcelWriter(output, engine="openpyxl", datetime_format="YYYY-MM-DD HH:MM:SS") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Inspection_Results")
        _apply_column_widths(writer, "Inspection_Results", export_df)

    return output.getvalue()

