# dashboards/memory.py
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from config import COLOR_MEM, COLOR_SWAP, COLOR_PROCESS

def render_memory_dashboard(st, df, parse_process_column, extract_process_time_series):
    st.subheader("Memory Analysis (512GB Capacity)")
    
    # 1. Memory Graph
    fig_mem = go.Figure()

    # Memory Area
    fig_mem.add_trace(go.Scatter(
        x=df['Timestamp'], y=df['Usage(%)'], 
        name='Physical Memory (%)', 
        mode='lines',
        line=dict(color=COLOR_MEM, width=2),
        fill='tozeroy'
    ))

    # Swap Line
    fig_mem.add_trace(go.Scatter(
        x=df['Timestamp'], y=df['Swap_Usage(%)'], 
        name='Swap Usage (%)', 
        mode='lines',
        line=dict(color=COLOR_SWAP, width=2)
    ))

    # Swap Start Annotation
    swap_start = df[df['Swap_Usage(%)'] > 1]['Timestamp'].min()
    if pd.notnull(swap_start):
        fig_mem.add_vline(x=swap_start, line_width=2, line_dash="dash", line_color="red", annotation_text="Swap Started")
        fig_mem.add_vrect(x0=swap_start, x1=df['Timestamp'].max(), fillcolor="red", opacity=0.1, layer="below", line_width=0)

    # Min/Max Annotations
    if not df.empty:
        min_mem_idx = df['Used(GB)'].idxmin()
        max_mem_idx = df['Used(GB)'].idxmax()
        if max_mem_idx > min_mem_idx:
             # Min point
            fig_mem.add_annotation(x=df.loc[min_mem_idx, 'Timestamp'], y=df.loc[min_mem_idx, 'Usage(%)'],
                                text="Start", showarrow=True, arrowhead=1)
            # Max point
            fig_mem.add_annotation(x=df.loc[max_mem_idx, 'Timestamp'], y=df.loc[max_mem_idx, 'Usage(%)'],
                                text="Peak", showarrow=True, arrowhead=1)

    fig_mem.update_layout(
        title="Physical Memory (Blue) vs Swap (Orange)",
        yaxis=dict(title="Usage (%)", range=[0, 100]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_mem, width='stretch')
    
    st.divider()
    
    # Top Memory Processes
    if 'Top5_Memory_MB' in df.columns:
        top_mem_df = parse_process_column(df['Top5_Memory_MB'])
        
        if not top_mem_df.empty:
            # --- TOP 3 Peak Chart ---
            st.subheader("🏆 Top 3 Heavy Memory Processes (Peak Usage)")
            top3 = top_mem_df.head(3)
            fig_bar = px.bar(top3, x='Process', y='Max_Value', 
                             title="Peak Memory Usage by Process (MB)", 
                             labels={'Max_Value': 'Peak Memory (MB)'}, text_auto='.0f')
            fig_bar.update_traces(marker_color=COLOR_PROCESS)
            st.plotly_chart(fig_bar, width='stretch')
            
            st.divider()
            
            # --- TOP 5 Selection & Trend Chart ---
            st.subheader("📈 Process Memory Trends (Top 5)")
            top5_names = top_mem_df.head(5)['Process'].tolist()
            
            st.write("Select processes to view their memory usage over time:")
            
            # Checkbox columns
            cols = st.columns(len(top5_names))
            selected_procs = []
            for i, name in enumerate(top5_names):
                if cols[i].checkbox(f"{name}", value=(i==0)): # Default select first one
                    selected_procs.append(name)
            
            if selected_procs:
                # Extract time series for all rows
                ts_df = extract_process_time_series(df, 'Top5_Memory_MB')
                if not ts_df.empty:
                    # Filter for selected processes
                    filtered_ts = ts_df[ts_df['Process'].isin(selected_procs)]
                    
                    if not filtered_ts.empty:
                        fig_trend = px.line(filtered_ts, x='Timestamp', y='Value', color='Process',
                                            title="Memory Usage Over Time (MB)",
                                            labels={'Value': 'Memory (MB)'})
                        fig_trend.update_layout(hovermode="x unified")
                        st.plotly_chart(fig_trend, width='stretch')
                    else:
                        st.info("No time-series data found for selected processes.")
                else:
                    st.info("No process data extracted from logs.")
            
            with st.expander("See Top 10 Details"):
                st.dataframe(top_mem_df.head(10))
        else:
            st.warning("No process data available.")

