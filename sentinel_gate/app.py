import streamlit as st
import pandas as pd
import os
import json
import tempfile
from datetime import datetime
from sentinel_gate.execution.orchestrator import run_data_quality_workflow
from sentinel_gate.utils.history_db import log_execution, get_history

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="SentinelGate Studio 🧬",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #0d6efd;
        color: white;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=100)
    st.title("SentinelGate Studio")
    st.info("The Low-Code Data Contract Platform")
    
    st.divider()
    st.subheader("Configurações Globais")
    chunk_size = st.number_input("Chunk Size", min_value=10, max_value=100000, value=1000)
    workers = st.slider("Parallel Workers", 1, 8, 2)
    save_hist = st.checkbox("Salvar no Histórico (history.db)", value=False)
    
    st.divider()
    st.caption("v3.5.0 - Parallel Edition")

# --- MAIN UI ---
st.title("🧬 SentinelGate Studio")
st.write("Governança e Qualidade de Dados simplificada.")

tabs = st.tabs(["📤 Upload & Config", "📊 Dashboard", "📜 Histórico"])

with tabs[0]:
    uploaded_file = st.file_uploader("Arraste seu dataset (CSV)", type=["csv"])
    
    if uploaded_file:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
            
        df_preview = pd.read_csv(tmp_path, nrows=5)
        st.write("### Preview dos Dados")
        st.dataframe(df_preview, use_container_width=True)
        
        st.divider()
        st.write("### 🛠️ Configurar Regras")
        
        # --- MAGIC BUTTON (AUTO DISCOVERY) ---
        if st.button("✨ Sugerir Regras Automaticamente (Discovery Engine)"):
             from sentinel_gate.discovery.engine import DiscoveryEngine
             disco = DiscoveryEngine(pd.read_csv(tmp_path))
             disco_res = disco.detect_primary_keys()
             
             st.session_state['default_null_cols'] = disco_res.get("columns", [])
             st.info(f"Sugestão: Detectamos que `{disco_res.get('columns')}` parece ser a Chave Primária. Adicionando Null-Checks sugeridos.")

        cols = df_preview.columns.tolist()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Null Checks**")
            default_nulls = st.session_state.get('default_null_cols', [])
            selected_null_cols = st.multiselect("Colunas que não podem ser nulas", options=cols, default=default_nulls)
            
        with col2:
            st.write("**Numeric Checks**")
            num_col = st.selectbox("Coluna Numérica", options=["None"] + cols)
            min_val = st.number_input("Valor Mínimo", value=0)
            
        st.divider()
        
        if st.button("🚀 EXECUTAR VALIDAÇÃO"):
            # Construct Contract
            quality_rules = {"null_checks": [], "numeric_checks": []}
            for c in selected_null_cols:
                quality_rules["null_checks"].append({"column": c, "max_percent": 0})
            
            if num_col != "None":
                quality_rules["numeric_checks"].append({"column": num_col, "min": min_val})
                
            contract = {
                "source": {
                    "type": "csv",
                    "file": tmp_path,
                    "chunk_size": chunk_size,
                    "parallel_workers": workers
                },
                "quality_rules": quality_rules,
                "discovery": {"detect_keys": True},
                "save_history": save_hist
            }
            
            with st.spinner("Executando Workflow SentinelGate..."):
                try:
                    result = run_data_quality_workflow(contract, output_dir="reports_ui")
                    st.success("Workflow concluído com sucesso!")
                    st.session_state['latest_result'] = result
                    st.session_state['latest_contract'] = contract
                    
                    # LOG TO HISTORY (Only if enabled)
                    if save_hist:
                        log_execution(result, contract)
                except Exception as e:
                    st.error(f"Erro na execução: {e}")

        if 'latest_contract' in st.session_state:
            st.write("### 📜 Contrato Gerado (JSON)")
            st.json(st.session_state['latest_contract'])
            st.download_button("Exportar Contrato (.json)", json.dumps(st.session_state['latest_contract'], indent=4), file_name="data_quality_contract.json")

with tabs[1]:
    if 'latest_result' in st.session_state:
        res = st.session_state['latest_result']
        
        st.header(f"Resultado: {res.get('status', 'N/A')}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Score de Qualidade", f"{res['scores']['final_score']}%")
        with c2:
            st.metric("Linhas Processadas", res.get('total_rows', 'Unknown'))
        with c3:
            st.metric("Modo de Execução", res.get('mode', 'N/A'))
            
        st.divider()
        st.write("### 📄 Relatório Técnico")
        report_path = res.get('report_path', 'Não disponível')
        st.info(f"O relatório detalhado foi gerado em: `{report_path}`")
        
        # Link to HTML report (in a real app, we would serve this file)
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                st.download_button("Baixar Relatório HTML", f.read(), file_name="sentinel_report.html", mime="text/html")
    else:
        st.warning("Nenhuma validação executada ainda.")

with tabs[2]:
    st.write("### Histórico de Execuções")
    history_data = get_history()
    
    if history_data:
        df_hist = pd.DataFrame(history_data)
        
        # Trend Chart
        st.write("#### Tendência de Qualidade")
        st.line_chart(df_hist.set_index("timestamp")["score"], color="#0d6efd")
        
        # Table
        st.write("#### Detalhes")
        st.dataframe(df_hist[["timestamp", "score", "total_rows", "mode", "status"]], use_container_width=True)
    else:
        st.info("Nenhuma execução registrada ainda.")

# --- FOOTER ---
st.divider()
st.caption("SentinelGate Framework | Powered by Antigravity AI")
