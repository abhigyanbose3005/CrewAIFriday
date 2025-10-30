import streamlit as st
from crewai import Agent, Task, Crew
from crewai_tools import RagTool
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure page
st.set_page_config(page_title="PDF Assistant", layout="centered")
st.title("📄 PDF Assistant")

# Ensure OpenAI API key is present
if not OPENAI_API_KEY:
    st.error("OpenAI API key not found. Please add OPENAI_API_KEY to your .env file.")
    st.stop()

# Reset vector DB state if new session
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    if "vector_db_initialized" in st.session_state:
        del st.session_state.vector_db_initialized

# File uploader
uploaded_file = st.file_uploader("Upload your PDF file", type=['pdf'])

if uploaded_file is not None:
    # Create temp directory if it doesn't exist
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"temp_{uploaded_file.name}")
    
    try:
        # Save uploaded file temporarily
        with st.spinner("Processing uploaded file..."):
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # --- Document loading & chunking (tune these) ---
            # chunk_size: 500-1200, overlap: 100-300 are good starting points
            chunk_size = 800
            chunk_overlap = 200

            loader = PyPDFLoader(temp_path)
            pages = loader.load()  # returns list of Documents (with page metadata)

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
            docs = text_splitter.split_documents(pages)

            # Optional: basic cleaning (strip, remove empty)
            for d in docs:
                d.page_content = d.page_content.strip()

            # --- Embeddings & vectorstore ---
            try:
                embedding_model = OpenAIEmbeddings(
                    openai_api_key=OPENAI_API_KEY
                )
            except Exception as e:
                st.error(f"Failed to initialize OpenAI embeddings: {str(e)}")
                st.stop()

            # Build (or load) FAISS vectorstore
            try:
                vector_db_path = os.path.join(os.path.dirname(__file__), "vector_db")
                os.makedirs(vector_db_path, exist_ok=True)
                # create in-memory FAISS index from docs
                vectorstore = FAISS.from_documents(docs, embedding_model)
            except Exception as e:
                st.error(f"Failed to build vector store: {str(e)}")
                st.stop()

            # Create an MMR retriever (more diverse, often better for relevance)
            retriever = vectorstore.as_retriever(
                search_type="mmr", 
                search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
            )

            # Initialize RAG tool as a fallback (if you still use it elsewhere)
            try:
                rag_tool = RagTool(
                    persist_directory=vector_db_path,
                    embedding_model=embedding_model
                )
            except Exception as e:
                # Not fatal for retrieval path; show warning
                st.warning(f"RagTool init failed (will still use retriever): {e}")
                rag_tool = None

            # Initialize chat if needed
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Display chat history
            for msg in st.session_state.messages:
                st.chat_message(msg["role"]).markdown(msg["content"])

            # Create PDF analysis agent (no internal retrieval here; we inject context manually)
            pdf_agent = Agent(
                role="PDF Analyst",
                goal="Analyze and answer questions about the PDF content",
                backstory="An expert in analyzing PDF documents and providing accurate information.",
                tools=[t for t in ([rag_tool] if rag_tool else [])],
                verbose=True,
                allow_delegation=False,
                temperature=0.0  # deterministic answers for retrieval QA
            )

            # Chat input
            user_input = st.chat_input("Ask something about the uploaded PDF...")

            if user_input:
                st.chat_message("user").markdown(user_input)
                st.session_state.messages.append({"role": "user", "content": user_input})

                with st.spinner("Retrieving relevant passages..."):
                    try:
                        # Retrieve relevant chunks (compatibility fallback)
                        if hasattr(retriever, "get_relevant_documents"):
                            top_docs = retriever.get_relevant_documents(user_input)[:5]
                        else:
                            # fallback to vectorstore similarity search (FAISS)
                            try:
                                top_docs = vectorstore.similarity_search(user_input, k=5)
                            except Exception:
                                # some builds return (doc, score) from similarity_search_with_score
                                ss = vectorstore.similarity_search_with_score(user_input, k=5)
                                top_docs = [doc for doc, _score in ss]


                        # Build a compact context to pass into the Task
                        context_parts = []
                        for i, d in enumerate(top_docs, start=1):
                            src = d.metadata.get("page", d.metadata.get("source", f"chunk-{i}"))
                            snippet = d.page_content.replace("\n", " ").strip()
                            # trim long snippets
                            if len(snippet) > 1000:
                                snippet = snippet[:1000].rsplit(" ", 1)[0] + "…"
                            context_parts.append(f"[Source: {src}]\n{snippet}")

                        context_text = "\n\n---\n\n".join(context_parts).strip()
                        if not context_text:
                            context_text = "No relevant text was found in the document."

                        # Construct a focused prompt that forces the agent to use the provided context and cite sources
                        task_description = (
                            "You are provided with context extracted from a PDF (below). Use ONLY this context to answer the question. "
                            "If the answer is not contained in the context, say you don't know. Cite the source labels in your answer.\n\n"
                            f"CONTEXT:\n{context_text}\n\nQUESTION:\n{user_input}\n\n"
                            "Answer concisely and include source citations like [Source: page_number] or [Source: chunk-1]."
                        )

                        # Run agent with the context-aware task
                        task = Task(
                            description=task_description,
                            expected_output=f"Answer and cite sources (from {uploaded_file.name})",
                            agent=pdf_agent
                        )
                        crew = Crew(agents=[pdf_agent], tasks=[task])
                        result = crew.kickoff()

                        st.chat_message("assistant").markdown(result)
                        st.session_state.messages.append({"role": "assistant", "content": result})
                    except Exception as e:
                        st.error(f"Error processing question: {str(e)}")

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
else:
    st.info("Please upload a PDF file to start the conversation.")