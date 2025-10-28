import streamlit as st
from crewai import Agent, Task, Crew
from crewai_tools import RagTool
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from google.auth.exceptions import DefaultCredentialsError

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="PDF Assistant", layout="centered")
st.title("📄 PDF Assistant")

# Ensure key is present
if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY not set. Add it to your .env (GEMINI_API_KEY=...) or environment and restart.")
    st.stop()

# File uploader
uploaded_file = st.file_uploader("Upload your PDF file", type=['pdf'])

if uploaded_file is not None:
    temp_path = f"temp_{uploaded_file.name}"
    try:
        # Save uploaded file temporarily
        with st.spinner("Processing uploaded file..."):
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Use GEMINI_API_KEY consistently for embeddings / llm
            try:
                embedding_model = GoogleGenerativeAIEmbeddings(
                    model="embedding-001",
                    api_key=GEMINI_API_KEY
                )

                llm = ChatGoogleGenerativeAI(
                    model="gemini-pro",
                    api_key=GEMINI_API_KEY
                )
            except DefaultCredentialsError as e:
                st.error(
                    "Google Application Default Credentials not found. "
                    "Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file or follow: "
                    "https://cloud.google.com/docs/authentication/external/set-up-adc"
                )
                st.stop()

            # Initialize session state for vector DB status
            if "vector_db_initialized" not in st.session_state:
                st.session_state.vector_db_initialized = False

            # Create vector DB directory if it doesn't exist
            vector_db_path = "./vector_db"
            os.makedirs(vector_db_path, exist_ok=True)

            # Initialize RAG tool with error handling
            try:
                rag_tool = RagTool(
                    persist_directory=vector_db_path,
                    embedding_model=embedding_model
                )
            except Exception as e:
                st.error(f"Failed to initialize RAG tool: {e}")
                st.stop()

            if not st.session_state.vector_db_initialized:
                with st.spinner("Loading PDF into vector database..."):
                    try:
                        rag_tool.add(data_type="file", path=temp_path)
                        st.session_state.vector_db_initialized = True
                    except Exception as e:
                        st.error(f"Error loading PDF: {e}")
                        st.stop()

            # Create agent (do not pass unknown/unofficial kwargs like MODEL/API_KEY)
            pdf_agent = Agent(
                role="PDF Analyst",
                goal="Answer questions based on the uploaded PDF",
                backstory="An expert in PDF analysis.",
                tools=[rag_tool],
                verbose=True,
                allow_delegation=False,
                temperature=0.5
            )

            if "messages" not in st.session_state:
                st.session_state.messages = []

            for msg in st.session_state.messages:
                st.chat_message(msg["role"]).markdown(msg["content"])

            user_input = st.chat_input("Ask something about the uploaded PDF...")

            if user_input:
                st.chat_message("user").markdown(user_input)
                st.session_state.messages.append({"role": "user", "content": user_input})

                with st.spinner("Analyzing your question..."):
                    try:
                        task = Task(
                            description=user_input,
                            expected_output=f"Answer based on the content of {uploaded_file.name}",
                            agent=pdf_agent
                        )

                        crew = Crew(agents=[pdf_agent], tasks=[task])
                        result = crew.kickoff()

                        st.chat_message("assistant").markdown(result)
                        st.session_state.messages.append({"role": "assistant", "content": result})
                    except Exception as e:
                        st.error(f"Error processing your question: {e}")
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
else:
    st.info("Please upload a PDF file to start the conversation.")