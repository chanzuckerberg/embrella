import os
from langchain.document_loaders import ConfluenceLoader
from langchain.text_splitter import CharacterTextSplitter, TokenTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain_openai.chat_models.base import BaseChatOpenAI
import markdown
from django.http import HttpResponse

from langchain.text_splitter import RecursiveCharacterTextSplitter
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
# from langchain.chains.qa_with_sources import load_qa_chain
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
import threading

# Constants
EMB_OPENAI_ADA = "text-embedding-ada-002"
EMB_SBERT = None # Chroma takes care

LLM_OPENAI_GPT35 = "gpt-3.5-turbo"
LLM_OPENAI_GPT40_MINI = "gpt-4o-mini"
LLM_OPENAI_GPT40 = "gpt-4o"

# Singleton ConfluenceQA instance
_qa_instance = None
_qa_init_lock = threading.Lock()

class ConfluenceQA:
    def __init__(self):
        self.embedding = None
        self.vectordb = None
        self.llm = None
        self.qa = None
        self.retriever = None
        self.is_initialized = False

    def init_embeddings(self) -> None:
        if self.embedding is None:
            self.embedding = OpenAIEmbeddings(
                model=EMB_OPENAI_ADA,
                api_key=os.environ["OPENAI_API_KEY"],
                timeout=30  # Add timeout
            )

    def init_models(self) -> None:
        if self.llm is None:
            self.llm = ChatOpenAI(
                model_name=LLM_OPENAI_GPT40_MINI,
                temperature=0.2,
                request_timeout=60  # Add timeout
            )

    def vector_db_confluence_docs(self, force_reload: bool = False) -> None:
        """
        Loads documents from Confluence, splits them, and creates/updates a Chroma vector DB.
        """
        if self.vectordb is not None and not force_reload:
            return  # Already initialized

        persist_directory = os.environ.get("persist_directory", "chroma_db")
        
        # Load existing vector database if available
        if not force_reload and os.path.exists(persist_directory):
            try:
                self.vectordb = Chroma(
                    persist_directory=persist_directory,
                    embedding_function=self.embedding
                )
                print("Loaded existing vector database.")
                return  # Early return if successfully loaded
            except Exception as e:
                print(f"Error loading vector database: {e}")
                # Continue with initialization

        # Only do confluence loading if needed
        confluence_url = os.environ.get("CONFLUENCE_URL", None)
        username = os.environ.get("USERNAME", None)
        api_key = os.environ.get("CONFLUENCE_KEY", None)
        space_keys = [
            key.strip()
            for key in os.environ.get("SPACE_KEYS", "").split(",")
            if key.strip()
        ]

        processed_keys_file = os.path.join(persist_directory, "processed_space_keys.json")
        processed_keys = []
        if os.path.exists(processed_keys_file):
            with open(processed_keys_file, "r") as f:
                processed_keys = json.load(f)

        # Identify new space keys that haven't been processed
        new_space_keys = [key for key in space_keys if key not in processed_keys]
        if not new_space_keys and self.vectordb is not None:
            print("No new space keys detected. Using existing DB.")
            return

        # Process new space keys
        all_documents = []
        for space_key in new_space_keys:
            try:
                loader = ConfluenceLoader(
                    url=confluence_url,
                    username=username,
                    api_key=api_key,
                    space_key=space_key
                )
                documents = loader.load(limit=400)
                for doc in documents:
                    doc.metadata["space_key"] = space_key
                all_documents.extend(documents)
                print(f"Loaded {len(documents)} documents from new space: {space_key}")
            except Exception as e:
                print(f"Error loading space {space_key}: {e}")
                continue

        # Ensure each document has a unique ID
        for doc in all_documents:
            if "id" not in doc.metadata:
                doc.metadata["id"] = str(hash(doc.page_content))

        existing_ids = set()
        if self.vectordb is not None:
            try:
                existing_data = self.vectordb._collection.get(
                    where={}, include=["metadatas"]
                )
                existing_ids = {
                    meta.get("id")
                    for meta in existing_data.get("metadatas", [])
                    if meta.get("id")
                }
            except Exception as e:
                print(f"Error fetching existing embeddings: {e}")

        new_documents = [
            doc
            for doc in all_documents
            if doc.metadata["id"] not in existing_ids
        ]
        
        if not new_documents and self.vectordb is not None:
            print("No new documents to embed.")
            processed_keys.extend(new_space_keys)
            with open(processed_keys_file, "w") as f:
                json.dump(processed_keys, f)
            return

        # Use a recursive text splitter with smaller chunks
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,  # Smaller chunks
            chunk_overlap=30,
            separators=["\n\n", "\n", " ", ""]
        )
        texts = recursive_splitter.split_documents(new_documents)

        try:
            if self.vectordb is None:
                self.vectordb = Chroma.from_documents(
                    documents=texts,
                    embedding=self.embedding,
                    persist_directory=persist_directory
                )
                print(f"Created a new vector database with {len(texts)} document chunks.")
            else:
                # Add in smaller batches to prevent memory issues
                batch_size = 100
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    self.vectordb.add_documents(batch)
                    print(f"Added batch of {len(batch)} document chunks.")
                print(f"Added total of {len(texts)} document chunks.")

            processed_keys.extend(new_space_keys)
            with open(processed_keys_file, "w") as f:
                json.dump(processed_keys, f)
        except Exception as e:
            print(f"Error updating vector database: {e}")
            raise

    def retreival_qa_chain(self):
        """
        Creates a retrieval QA chain using the 'stuff' chain type for better performance.
        """
        if self.qa is not None:
            return  # Already initialized

        # Simplified prompt template
        custom_prompt_template = """You are a Confluence chatbot designed to answer questions about the CZII wiki. Use the provided context to respond accurately and informatively. If you don't know the answer, say that you don't know; do not make up an answer.

        ---

        ## Response Rules

        1. **General Questions (e.g., greetings, navigation, number of wikis, availability)**  
        - Provide a **concise response (under 50 words)**.  
        - Keep the tone **friendly and professional**.  

        2. **Technical or Detailed Queries (e.g., CryoET, pipeline processes, workflows, or research topics)**  
        - Provide a **thorough response (at least 250 words)**.  
        - Use **clear headings** (e.g., "### Introduction", "### Key Details", "### Conclusion").  
        - Separate headings with a **blank line** beneath them for readability.  
        - Use **short paragraphs** (5–7 sentences), and put a **blank line** between paragraphs.  
        - Use **bullet points** or **numbered lists** for enumerations or key points.  
        - **Bold** or *italicize* key terms to emphasize important concepts or definitions.

        3. **Output Formatting**  
        - Do not create large blocks of text; use **blank lines** to break up sections.  
        - Ensure the final output is **readable** and well-structured.

        ---

        ## Context
        {context}

        ## User Question
        {question}

        ---
        """

        CUSTOM_PROMPT = PromptTemplate(
            template=custom_prompt_template, 
            input_variables=["context", "question"]
        )

        # Create the retriever
        self.retriever = self.vectordb.as_retriever(search_kwargs={"k": 4})  # Reduced from 6

        # Use 'stuff' chain type for better performance
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",  # Changed from 'refine' to 'stuff'
            retriever=self.retriever,
            return_source_documents=False,  # Changed to False
            chain_type_kwargs={"prompt": CUSTOM_PROMPT}
        )

    def initialize(self):
        """Initialize all components if not already done"""
        if not self.is_initialized:
            try:
                self.init_embeddings()
                self.init_models()
                self.vector_db_confluence_docs()
                self.retreival_qa_chain()
                self.is_initialized = True
            except Exception as e:
                print(f"Initialization error: {e}")
                raise

    def answer_confluence(self, question: str) -> str:
        """
        Retrieves relevant chunks and produces an answer for the provided question.
        """
        try:
            result = self.qa({"query": question})
            # The result structure depends on the chain type
            if isinstance(result, dict):
                answer = result.get("result", "")
            else:
                answer = str(result)
            
            return answer
        except Exception as e:
            print(f"Error generating answer: {e}")
            return f"Sorry, I encountered an error while processing your question: {str(e)}"


def get_qa_instance():
    """Get or create the singleton QA instance"""
    global _qa_instance
    if _qa_instance is None:
        with _qa_init_lock:  # Thread safety
            if _qa_instance is None:
                _qa_instance = ConfluenceQA()
    return _qa_instance


@csrf_exempt
def api_answer(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            question = payload.get('prompt', None)

            if not question:
                return JsonResponse({'error': 'Prompt is required.'}, status=400)

            # Get the singleton instance
            agent = get_qa_instance()
            
            # Initialize if not already done (only happens once)
            if not agent.is_initialized:
                try:
                    agent.initialize()
                except Exception as e:
                    error_msg = f"Failed to initialize QA system: {str(e)}"
                    print(error_msg)
                    return JsonResponse({'error': error_msg}, status=500)
            
            # Generate answer with timeout
            try:
                answer = agent.answer_confluence(question)
                html_answer = markdown.markdown(answer)
                return HttpResponse(html_answer, content_type="text/html")
            except Exception as e:
                error_msg = f"Error generating answer: {str(e)}"
                print(error_msg)
                return JsonResponse({'error': error_msg}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
        except Exception as e:
            print(f"Unexpected error in api_answer: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)