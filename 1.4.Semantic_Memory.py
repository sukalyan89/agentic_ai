import hashlib
import io
import os
import re
from pathlib import Path

import chromadb
import numpy as np
import pandas as pd
import streamlit as st
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

st.set_page_config(page_title="Semantic Memory Explorer", page_icon="🧠", layout="wide")
st.title("🧠 Semantic Memory Explorer")
st.caption("Upload → Chunk → Embed → Store → Search. A visual ChromaDB demonstration.")

DB_DIR = str(Path(__file__).resolve().parent / "chroma_data")
DEFAULT_COLLECTION = "webinar_semantic_memory"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

@st.cache_resource(show_spinner="Loading local embedding model...")
def load_model():
    return SentenceTransformer(MODEL_NAME)

@st.cache_resource
def get_client():
    return chromadb.PersistentClient(path=DB_DIR)

model = load_model()
client = get_client()
client.get_or_create_collection(
    name=DEFAULT_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)


def list_collection_names():
    return sorted(
        collection.name if hasattr(collection, "name") else collection
        for collection in client.list_collections()
    )


collection_names = list_collection_names()
if not collection_names:
    st.error(f"No Chroma collections found in {DB_DIR}.")
    st.stop()

def extract_text(file):
    data = file.getvalue()
    if file.name.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = data.decode("utf-8-sig", errors="replace")
    return text

def split_text(text, chunk_size=600, overlap=100):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + int(chunk_size * .65), end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks

def embed(texts):
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def get_memory_source(metadata):
    metadata = metadata or {}
    return (
        metadata.get("source")
        or metadata.get("policy_id")
        or metadata.get("title")
        or metadata.get("section")
        or "Unknown source"
    )


def get_memory_chunk(metadata):
    metadata = metadata or {}
    return (
        metadata.get("chunk_index")
        or metadata.get("subsection")
        or metadata.get("category")
        or "N/A"
    )


with st.sidebar:
    st.header("⚙️ Vector database")
    st.write("**Engine:** ChromaDB (persistent)")
    st.write("**Embedding:** all-MiniLM-L6-v2")
    selected_collection = st.selectbox(
        "Chroma collection",
        options=collection_names,
        index=(
            collection_names.index(DEFAULT_COLLECTION)
            if DEFAULT_COLLECTION in collection_names
            else 0
        ),
    )
    collection = client.get_collection(name=selected_collection)
    st.metric("Stored chunks", collection.count())
    st.caption(f"Storage: {DB_DIR}")
    st.warning("Demo only: uploaded content stays on the machine running Streamlit. Do not upload confidential customer data.")
    if st.button("🗑️ Delete selected collection", use_container_width=True):
        client.delete_collection(selected_collection)
        st.cache_resource.clear()
        st.rerun()

tab_upload, tab_search, tab_explore = st.tabs(["📥 Upload & Store", "🔎 Semantic Search", "🗂️ Memory Explorer"])

with tab_upload:
    st.subheader("Add information to semantic memory")
    uploads = st.file_uploader("Upload text, Markdown, or text-based PDFs", type=["txt", "md", "pdf"], accept_multiple_files=True)
    a, b = st.columns(2)
    with a:
        chunk_size = st.slider("Chunk size (characters)", 100, 1200, 600, 50)
    with b:
        overlap = st.slider("Overlap (characters)", 0, 250, 100, 25)
    if uploads and st.button("Generate embeddings & store", type="primary"):
        inserted = 0
        for upload in uploads:
            content = extract_text(upload)
            chunks = split_text(content, chunk_size, min(overlap, chunk_size - 1))
            if not chunks:
                st.warning(f"No extractable text found in {upload.name}. Scanned PDFs require OCR.")
                continue
            digest = hashlib.sha256(upload.getvalue()).hexdigest()[:16]
            ids = [f"{digest}-{chunk_size}-{overlap}-{i}" for i in range(len(chunks))]
            vectors = embed(chunks)
            for start in range(0, len(chunks), 100):
                end = start + 100
                collection.upsert(
                    ids=ids[start:end], documents=chunks[start:end], embeddings=vectors[start:end],
                    metadatas=[{"source": upload.name, "chunk_index": i, "file_hash": digest} for i in range(start, min(end, len(chunks)))]
                )
            inserted += len(chunks)
            st.success(f"{upload.name}: stored {len(chunks)} chunks")
        st.info(f"Processed {inserted} chunks. Re-uploading identical files with identical settings updates existing IDs.")
    st.caption("Embeddings are computed locally. The first run downloads the model from Hugging Face.")

with tab_search:
    st.subheader("Find related memories by meaning")
    query = st.text_input("Search query", placeholder="e.g., How can an agent remember previous customer preferences?")
    k = st.slider("Number of results", 1, 10, 5)
    if st.button("Search semantic memory", type="primary", disabled=not query.strip()):
        if collection.count() == 0:
            st.warning("Upload some documents first.")
        else:
            qvec = embed([query])[0]
            results = collection.query(query_embeddings=[qvec], n_results=min(k, collection.count()), include=["documents", "metadatas", "distances", "embeddings"])
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]
            vectors = np.asarray(results["embeddings"][0], dtype=float)
            scores = [max(0.0, min(1.0, 1.0 - float(d))) for d in distances]
            st.caption("Scores = 1 − cosine distance. They indicate vector similarity, not probability of correctness.")
            sources = [get_memory_source(meta) for meta in metas]
            chunks = [get_memory_chunk(meta) for meta in metas]
            df = pd.DataFrame({"Rank": range(1, len(docs) + 1), "Source": sources, "Chunk": chunks, "Similarity": scores})
            st.bar_chart(df.set_index("Rank")["Similarity"], y_label="Cosine similarity")
            for i, (doc, meta, score) in enumerate(zip(docs, metas, scores), start=1):
                with st.expander(f"#{i} · {get_memory_source(meta)} · similarity {score:.3f}", expanded=(i == 1)):
                    st.write(doc)
                    st.caption(f"Chunk: {get_memory_chunk(meta)}")
            st.subheader("🗺️ Embedding projection (PCA)")
            if len(vectors) >= 2:
                from sklearn.decomposition import PCA
                points = np.vstack([vectors, np.asarray(qvec)[None, :]])
                xy = PCA(n_components=2).fit_transform(points)
                plot_df = pd.DataFrame({"PC1": xy[:, 0], "PC2": xy[:, 1], "Point": [f"Result {i}" for i in range(1, len(vectors)+1)] + ["SEARCH QUERY"]})
                st.scatter_chart(plot_df, x="PC1", y="PC2", color="Point")
                st.caption("Illustrative 2D projection of high-dimensional vectors; distances in this plot do not exactly preserve original cosine similarities.")
            else:
                st.info("Retrieve at least two chunks to show a 2D projection.")

with tab_explore:
    st.subheader("Stored semantic memories")
    total = collection.count()
    st.metric("Total chunks", total)
    if total:
        limit = st.slider("Rows to inspect", 1, min(200, total), min(25, total))
        records = collection.get(limit=limit, include=["documents", "metadatas"])
        rows = [
            {
                "ID": record_id,
                "Source": get_memory_source(metadata),
                "Chunk": get_memory_chunk(metadata),
                "Text": document or "",
                "Metadata": metadata or {},
            }
            for record_id, metadata, document in zip(
                records["ids"],
                records["metadatas"],
                records["documents"],
            )
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("This table displays stored text and metadata. ChromaDB also stores embedding vectors for retrieval.")
    else:
        st.info("The collection is empty. Upload a document to get started.")
