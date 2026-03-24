# Data Loading Optimization Strategy

To significantly reduce the loading time for large datasets (e.g., 3 days of logs), we recommend the following structural changes and optimizations.

## 1. Upgrade CSV Reading Engine (Single Core Boost)
Switch the pandas CSV engine to `pyarrow`. This is typically **multi-threaded internally** and much faster than the default C engine.
- **Before**: `pd.read_csv(f, low_memory=False)`
- **After**: `pd.read_csv(f, engine="pyarrow", dtype_backend="pyarrow")` (if available) or minimally `engine="c"` (default but double check). Actually `engine="pyarrow"` is the key.

## 2. Parallel Processing (Multi-Threading)
Instead of processing files one by one (Sequential Loop), we can process them in parallel. Since the main bottleneck is likely I/O and parsing (which releases the GIL in pandas C extensions), `ThreadPoolExecutor` is effective and simpler to implement than `ProcessPoolExecutor` (especially with Streamlit's in-memory `UploadedFile` objects).

### Proposed Structure

#### A. Modularize File Processing
Extract the logic for processing a **single file** into a standalone function. This function takes a file (or path) and returns a processed DataFrame (or `None`).

```python
def process_single_file(file):
    """
    Reads and processes a single log file (Logman or Monitor).
    Returns: (type, dataframe) or None
    """
    try:
        # Determine filename/type
        fname = file if isinstance(file, str) else file.name
        
        # 1. Read CSV (Optimized)
        # Use pyarrow engine for speed if possible, else standard C
        try:
            df = pd.read_csv(file, engine='pyarrow') 
        except:
            df = pd.read_csv(file, low_memory=False) # Fallback
            
        # 2. Process based on type (Logman vs Process)
        if "Global_Usage" in fname:
            # ... (Existing Logman cleaning logic: rename cols, Regex drive letters, etc.) ...
            return ('logman', df)
            
        else:
            # ... (Existing Monitor cleaning logic) ...
            return ('process', df)
            
    except Exception as e:
        return None
```

#### B. Parallel Execution in `load_data`
Update the main `load_data` function to use a `ThreadPoolExecutor`.

```python
from concurrent.futures import ThreadPoolExecutor

@st.cache_data
def load_data(files):
    logman_dfs = []
    process_dfs = []
    
    # Process files in parallel
    with ThreadPoolExecutor() as executor:
        results = executor.map(process_single_file, files)
        
    # Collect results
    for result in results:
        if result is None: continue
        
        rtype, df = result
        if rtype == 'logman':
            logman_dfs.append(df)
        elif rtype == 'process':
            process_dfs.append(df)
            
    # ... (Existing Merge Logic: concat and merge_asof) ...
```

## 3. Benefits
1.  **Concurrency**: Multiple files are read and parsed simultaneously, utilizing multi-core CPUs better (despite Python GIL, pandas releases it for heavy lifting).
2.  **Responsiveness**: The UI will feel faster as the total wait time is determined by the *longest* file group rather than the *sum* of all files.
3.  **Scalability**: Works well whether you load 3 files or 30 files.

## 💻 2026-03-24 업데이트 (Python Native Collector 도입)

기존 Logman/PowerShell 혼합 수집 방식에서 발생하던 병합 성능 문제와 `merge_asof` 로직의 한계를 극복하기 위해, **Python `psutil` 기반의 Native Collector** 아키텍처로 전면 개편되었습니다.

### 주요 변경 사항
1. **1초 샘플링 / 5초 집계 (Peak/Avg)** 로직으로 통일하여 Logman과 PowerShell의 수집 주기가 어긋나던 문제를 원천 해결.
2. `data_loader.py` 내부의 복잡한 `merge_asof` 및 정규식 컬럼 파싱 로직을 제거하고, 정확한 `Timestamp` 기준의 `pd.merge` 체계로 단순화.
3. 생성되는 CSV 포맷을 대시보드 구조에 완벽히 호환되도록 정규화(`resource_*.csv`, `process_*.csv`).
