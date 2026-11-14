"""Streamlit interface for the project's private research library."""
import os

import streamlit as st

from research_rag import (
    DEFAULT_EMBEDDING_MODEL,
    delete_research_document,
    embed_texts,
    index_document,
    list_research_documents,
    retrieve_relevant_chunks,
)


def render_research_library(project_id, ollama_url):
    """Upload, index, inspect and search source documents for one project."""
    st.subheader("📚 Research Library (RAG)")
    st.caption(
        "Add source documents to this project's private library. Screenwriter Studio "
        "retrieves relevant excerpts by semantic similarity and keeps source labels."
    )
    if project_id is None:
        st.info("Create or load a project before adding research documents.")
        return

    model_key = "research_embedding_model"
    st.text_input(
        "Embedding model (Ollama)",
        value=os.getenv("OLLAMA_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        key=model_key,
        help="Default: nomic-embed-text:latest. Pull it once with: ollama pull nomic-embed-text",
    )
    uploaded_files = st.file_uploader(
        "Upload research sources",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        key="research_file_uploader",
        help="PDF, DOCX, TXT and Markdown. Each file must be 10 MB or smaller.",
    )
    if st.button("＋ Index uploaded documents", use_container_width=True, key="index_research_button"):
        if not uploaded_files:
            st.warning("Choose at least one file to index.")
        else:
            for uploaded in uploaded_files:
                try:
                    with st.spinner(f"Extracting and indexing {uploaded.name}…"):
                        result = index_document(
                            project_id, uploaded.name, uploaded.getvalue(),
                            st.session_state[model_key],
                            lambda texts, model: embed_texts(texts, model, ollama_url),
                        )
                    st.success(
                        f"{result['file_name']}: {result['chunk_count']} chunks indexed."
                    )
                except Exception as exc:
                    st.error(f"{uploaded.name}: {exc}")

    documents = list_research_documents(project_id)
    if documents:
        st.markdown("#### Indexed sources")
        for document in documents:
            left, right = st.columns([5, 1])
            with left:
                st.write(f"**{document['file_name']}** · {document['chunk_count']} chunks")
                st.caption(f"Embedding model: {document['embedding_model']} · Added: {document['created_at']}")
            with right:
                if st.button("Delete", key=f"delete_research_{document['id']}"):
                    delete_research_document(document["id"], project_id)
                    st.rerun()
    else:
        st.info("No research sources indexed for this project yet.")

    st.markdown("#### Search the research library")
    query = st.text_input(
        "Ask a research question",
        placeholder="What historical details could make this setting authentic?",
        key="research_search_query",
    )
    top_k = st.slider("Number of excerpts", 1, 10, 5, key="research_top_k")
    if st.button("Search sources", key="search_research_button", disabled=not bool(documents)):
        try:
            with st.spinner("Finding relevant excerpts…"):
                results = retrieve_relevant_chunks(
                    project_id, query, st.session_state[model_key],
                    lambda texts, model: embed_texts(texts, model, ollama_url),
                    top_k=top_k,
                )
            st.session_state["research_search_results"] = results
            st.session_state["research_search_project_id"] = project_id
        except Exception as exc:
            st.error(f"Research search failed: {exc}")

    results = st.session_state.get("research_search_results", [])
    if st.session_state.get("research_search_project_id") == project_id and results:
        for index, item in enumerate(results, start=1):
            page = f" · page {item['page_number']}" if item.get("page_number") else ""
            with st.expander(
                f"[R{index}] {item['file_name']}{page} · similarity {item['score']:.3f}",
                expanded=index == 1,
            ):
                st.write(item["content"])
    elif query and documents:
        st.caption("Run a search to see source excerpts.")
