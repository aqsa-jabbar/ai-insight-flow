"""
app.py
------
Streamlit frontend for the AI Research & Report Generator.

Flow:
1. User enters a website URL or platform name.
2. We call our stateless LangGraph agent to generate a structured report.
3. The report (and only that report) is stored in st.session_state, so the
   user can ask follow-up questions about it.
4. If the user enters a NEW link/topic, the old report is replaced -
   there is no memory of the previous link.
"""

import streamlit as st
from dotenv import load_dotenv
from agent_setup import run_agent
from export_utils import generate_docx, generate_pdf

# Loads SERPER_API_KEY and GROQ_API_KEY from a local .env file.
# On Hugging Face Spaces, these come from Repository Secrets instead,
# and load_dotenv() simply does nothing there (which is fine).
load_dotenv()

st.set_page_config(page_title="AI Website Research Agent", page_icon="🔎")
st.title("🔎 SiteSage AI")
st.caption("Enter a website URL or a platform/company name to generate a research report.")

# ---------------------------------------------------------------------
# Session state setup
# ---------------------------------------------------------------------
# current_target -> the link/topic the current report belongs to
# report          -> the generated report text for that target only
if "current_target" not in st.session_state:
    st.session_state.current_target = None
    st.session_state.report = None

target = st.text_input("Enter a website URL or platform name:", placeholder="e.g. https://stripe.com or 'Notion'")

if st.button("Generate Report", type="primary") and target:
    # A new target always overwrites/resets the previous report.
    # This is what keeps the app "no memory across links."
    st.session_state.current_target = target
    st.session_state.report = None

    with st.spinner("Researching... this may take a moment"):
        try:
            prompt = f"Give me a full research report on: {target}"
            st.session_state.report = run_agent(prompt)
        except Exception as e:
            st.error(f"Something went wrong while generating the report: {e}")

# ---------------------------------------------------------------------
# Display report + Q&A section
# ---------------------------------------------------------------------
if st.session_state.report:
    st.subheader(f"Report on: {st.session_state.current_target}")
    st.write(st.session_state.report)

    # ---- Download options ----
    report_title = f"Research Report - {st.session_state.current_target}"
    col1, col2 = st.columns(2)

    with col1:
        docx_bytes = generate_docx(report_title, st.session_state.report)
        st.download_button(
            label="⬇️ Download as Word (.docx)",
            data=docx_bytes,
            file_name="research_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    with col2:
        pdf_bytes = generate_pdf(report_title, st.session_state.report)
        st.download_button(
            label="⬇️ Download as PDF",
            data=pdf_bytes,
            file_name="research_report.pdf",
            mime="application/pdf",
        )

    st.divider()
    st.subheader("Ask a question about this link/topic")
    question = st.text_input("Your question:", key="qa_input")

    if st.button("Ask") and question:
        with st.spinner("Thinking..."):
            try:
                # We manually re-inject the report as context here instead of
                # using memory or RAG. This is intentional: it's the simplest
                # way to let the user ask about "this same report" without
                # keeping any conversational state inside the agent itself.
                qa_prompt = (
                    f"Context: earlier report about {st.session_state.current_target}:\n"
                    f"{st.session_state.report}\n\n"
                    f"Now answer this question strictly using that context: {question}"
                )
                answer = run_agent(qa_prompt)
                st.write(answer)
            except Exception as e:
                st.error(f"Something went wrong while answering: {e}")