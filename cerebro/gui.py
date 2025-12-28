import streamlit as st
import os
import re
import time
import ollama
from streamlit_agraph import agraph
from cerebro.ingester import Ingester, CerebroChunk
from cerebro.tracer import CerebroTracer
from cerebro.validator import CerebroValidator
from cerebro.vector_store import CerebroVectorStore
from cerebro.reporter import CerebroReporter
from cerebro.graph import CerebroGraph

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="CerebroScope", 
    page_icon="🔍", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimal CSS
def inject_custom_css():
    st.markdown("""
    <style>
        .verdict-box { 
            border-left: 5px solid #ffc107; 
            background-color: #fff3cd; 
            padding: 15px; 
            margin: 20px 0; 
            border-radius: 5px;
            color: #856404;
        }
        .evidence-card {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            color: #212529;
        }
        .evidence-used {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-left: 5px solid #28a745;
            color: #155724;
        }
        .highlight-id {
            background-color: #d1ecf1;
            color: #0c5460;
            padding: 2px 5px;
            border-radius: 4px;
            font-weight: bold;
            font-family: monospace;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 2. INITIALIZATION ---
@st.cache_resource
def get_components():
    return {
        "ingester": Ingester(),
        "tracer": CerebroTracer(),
        "validator": CerebroValidator(),
        "vector_db": CerebroVectorStore(),
        "reporter": CerebroReporter(),
        "graph": CerebroGraph()
    }

components = get_components()

# --- 3. OLLAMA FIX ---
def get_ollama_models():
    try:
        models_info = ollama.list()
        if hasattr(models_info, 'models'):
            raw_models = models_info.models
        elif isinstance(models_info, dict) and 'models' in models_info:
            raw_models = models_info['models']
        else:
            raw_models = []

        clean_names = []
        for m in raw_models:
            if isinstance(m, dict):
                name = m.get('name') or m.get('model')
            else:
                name = getattr(m, 'model', getattr(m, 'name', None))
            if name: clean_names.append(name)
                
        return clean_names if clean_names else ["llama3"]
    except:
        return ["llama3 (Offline)"]

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Control Panel")
    
    # Model Selection
    st.subheader("1. Select AI Model")
    available_models = get_ollama_models()
    selected_model = st.selectbox("Active Model:", available_models)

    st.divider()

    # File Upload
    st.subheader("2. Add Documents")
    uploaded_files = st.file_uploader("Upload files (PDF, CSV, TXT)", accept_multiple_files=True)
    if uploaded_files:
        if st.button("Process Files", type="primary", use_container_width=True):
            with st.spinner("Processing..."):
                raw_path = "data/raw"
                if not os.path.exists(raw_path): os.makedirs(raw_path)
                for uploaded_file in uploaded_files:
                    with open(os.path.join(raw_path, uploaded_file.name), "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                new_chunks = components["ingester"].ingest_directory(raw_path)
                if new_chunks:
                    components["vector_db"].add_chunks(new_chunks)
                    st.success(f"Added {len(new_chunks)} fragments!")
                else:
                    st.warning("No text found.")

    st.divider()

    # Scope Filter
    st.subheader("3. Target Scope")
    raw_path = "data/raw"
    existing_files = os.listdir(raw_path) if os.path.exists(raw_path) else []
    selected_sources = st.multiselect("Search only in:", existing_files, placeholder="All files")

    st.divider()
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

# --- 5. MAIN INTERFACE ---

st.title("🔍 CerebroScope Analysis")

if "messages" not in st.session_state:
    st.session_state.messages = []

if len(st.session_state.messages) == 0:
    st.info("👋 Hi! Upload files in the sidebar and ask a question to start the analysis.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

if query := st.chat_input("Ask a question regarding the documents..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        with st.spinner("Analyzing documents..."):
            # 1. Retrieval
            db = components["vector_db"]
            results = db.search(query, n_results=5, source_filter=selected_sources)
            
            retrieved_chunks = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    meta = results['metadatas'][0][i]
                    chunk = CerebroChunk(
                        chunk_id=results['ids'][0][i],
                        text=results['documents'][0][i],
                        source=meta['source'],
                        page=meta['page'],
                        timestamp=meta.get('timestamp', time.time())
                    )
                    chunk.reliability_score = components["validator"].calculate_reliability_score(chunk)
                    retrieved_chunks.append(chunk)
            
            # 2. Logic & Tracing
            conflicts = components["validator"].check_for_conflicts(retrieved_chunks, model_name=selected_model)
            answer = components["tracer"].analyze_query(query, retrieved_chunks, model_name=selected_model)
            
            # 3. Reporting
            report_path = components["reporter"].save_report(query, answer, conflicts, retrieved_chunks)
            with open(report_path, "rb") as f: report_data = f.read()

            placeholder.empty()

            # 4. Final Render
            highlighted_answer = re.sub(
                r"(\[ID: [a-f0-9]+\])", 
                r"<span class='highlight-id'>\1</span>", 
                answer
            )
            st.markdown(highlighted_answer, unsafe_allow_html=True)
            
            st.download_button("📥 Download Report (.md)", report_data, file_name=os.path.basename(report_path))

            if "CONFLICT" in conflicts:
                st.markdown(f"""<div class="verdict-box"><h4>⚠️ CONFLICT DETECTED</h4>{conflicts}</div>""", unsafe_allow_html=True)
            
            # Tabs
            tab_graph, tab_evid, tab_data = st.tabs(["🕸️ Graph View", "🔍 Evidence", "📊 Data Table"])
            used_ids = re.findall(r"ID: ([a-f0-9]+)", answer)

            with tab_graph:
                if retrieved_chunks:
                    nodes, edges, config = components["graph"].visualize_connections(retrieved_chunks)
                    if nodes: agraph(nodes=nodes, edges=edges, config=config)
                    else: st.info("No entities found to visualize.")
                else: st.info("No data found.")

            with tab_evid:
                for c in retrieved_chunks:
                    is_used = any(u in c.chunk_id for u in used_ids)
                    css_class = "evidence-card evidence-used" if is_used else "evidence-card"
                    status = "✅ USED" if is_used else "❌ IGNORED"
                    
                    st.markdown(f"""
                    <div class="{css_class}">
                        <div style="display:flex; justify-content:space-between; font-weight:bold;">
                            <span>{status} | ID: {c.chunk_id}</span>
                            <span style="color:#007bff;">{c.source}</span>
                        </div>
                        <div style="margin: 5px 0; font-family:sans-serif;">{c.text[:300]}...</div>
                        <div style="font-size:0.8em; color:#666;">Reliability: {c.reliability_score}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(c.reliability_score/100)

            with tab_data:
                st.dataframe([{"ID": c.chunk_id, "Source": c.source, "Score": c.reliability_score} for c in retrieved_chunks], use_container_width=True)

            st.session_state.messages.append({"role": "assistant", "content": highlighted_answer})