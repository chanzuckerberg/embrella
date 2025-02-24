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

# Constants
EMB_OPENAI_ADA = "text-embedding-ada-002"
EMB_SBERT = None # Chroma takes care

LLM_OPENAI_GPT35 = "gpt-3.5-turbo"
LLM_OPENAI_GPT40_MINI = "gpt-4o-mini"
LLM_OPENAI_GPT40 = "gpt-4o"


# class ConfluenceQA:
#     def __init__(self):

#         self.embedding = None
#         self.vectordb = None
#         self.llm = None
#         self.qa = None
#         self.retriever = None
#     def init_embeddings(self) -> None:
#         # OpenAI ada embeddings API
#         # self.embedding = OpenAIEmbeddings()
#         self.embedding = OpenAIEmbeddings(model="text-embedding-3-small",api_key=os.environ['OPENAI_API_KEY'])
#     def init_models(self) -> None:
#         # OpenAI GPT 3.5 API
#         self.llm = ChatOpenAI(model_name=LLM_OPENAI_GPT40, temperature=0.4)


#     def vector_db_confluence_docs(self, force_reload: bool = False) -> None:
#         persist_directory = os.environ.get("persist_directory", "chroma_db")
#         confluence_url = os.environ.get("CONFLUENCE_URL", None)
#         username = os.environ.get("USERNAME", None)
#         api_key = os.environ.get("CONFLUENCE_KEY", None)
#         space_keys = [key.strip() for key in os.environ.get("SPACE_KEYS", "").split(",") if key.strip()]

#         processed_keys_file = os.path.join(persist_directory, "processed_space_keys.json")
#         processed_keys = []
#         if os.path.exists(processed_keys_file):
#             with open(processed_keys_file, "r") as f:
#                 processed_keys = json.load(f)

#         # Load existing vector database if available
#         if not force_reload and os.path.exists(persist_directory):
#             self.vectordb = Chroma(persist_directory=persist_directory, embedding_function=self.embedding)
#             print("Loaded existing vector database.")
#         else:
#             self.vectordb = None

#         # Identify new space keys that haven't been processed
#         new_space_keys = [key for key in space_keys if key not in processed_keys]
        
#         if not new_space_keys:
#             print("No new space keys detected. Skipping new embedding.")
#             # Here, if self.vectordb is already loaded, you can continue using it.
#             return

#         # Proceed with embedding for new space keys...
#         all_documents = []
#         for space_key in new_space_keys:
#             loader = ConfluenceLoader(
#                 url=confluence_url,
#                 username=username,
#                 api_key=api_key,
#                 space_key=space_key
#             )
#             documents = loader.load(limit=400)
#             for doc in documents:
#                 doc.metadata["space_key"] = space_key
#             all_documents.extend(documents)
#             print(f"Loaded {len(documents)} documents from new space: {space_key}")

#         for doc in all_documents:
#             if "id" not in doc.metadata:
#                 doc.metadata["id"] = str(hash(doc.page_content))

#         existing_ids = set()
#         if self.vectordb is not None:
#             try:
#                 existing_data = self.vectordb._collection.get(where={}, include=["metadatas"])
#                 existing_ids = {meta.get("id") for meta in existing_data.get("metadatas", []) if meta.get("id")}
#             except Exception as e:
#                 print(f"Error fetching existing embeddings: {e}")

#         new_documents = [doc for doc in all_documents if doc.metadata["id"] not in existing_ids]

#         if not new_documents:
#             print("No new documents to embed.")
#             processed_keys.extend(new_space_keys)
#             with open(processed_keys_file, "w") as f:
#                 json.dump(processed_keys, f)
#             return

#         # Use text splitters and add documents to the vector database as before
#         char_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=0)
#         texts = char_splitter.split_documents(new_documents)
#         token_splitter = TokenTextSplitter(chunk_size=200, chunk_overlap=10, encoding_name="cl100k_base")
#         texts = token_splitter.split_documents(texts)

#         if self.vectordb is None:
#             self.vectordb = Chroma.from_documents(documents=texts, embedding=self.embedding, persist_directory=persist_directory)
#             print(f"Created a new vector database with {len(texts)} document chunks.")
#         else:
#             self.vectordb.add_documents(texts)
#             print(f"Added {len(texts)} new document chunks to the existing vector database.")

#         processed_keys.extend(new_space_keys)
#         with open(processed_keys_file, "w") as f:
#             json.dump(processed_keys, f)

#     def retreival_qa_chain(self):
#         """
#         Creates retrieval QA chain using vectordb as retriever and LLM to complete the prompt
#         """
#         # Define the custom prompt
#         custom_prompt_template = """You are a Confluence chatbot designed to answer questions about the company's wiki. Use the provided context to respond accurately and informatively. If you don't know the answer, say that you don't know; do not make up an answer.

#         ---

#         ## Response Rules

#         1. **General Questions (e.g., greetings, navigation, number of wikis, availability)**  
#         - Provide a **concise response (under 300 words)**.  
#         - Keep the tone **friendly and professional**.  

#         2. **Technical or Detailed Queries (e.g., CryoET, pipeline processes, workflows, or research topics)**  
#         - Provide a **thorough response (at least 250 words)**.  
#         - Use **clear headings** (e.g., "### Introduction", "### Key Details", "### Conclusion").  
#         - Separate headings with a **blank line** beneath them for readability.  
#         - Use **short paragraphs** (5–7 sentences), and put a **blank line** between paragraphs.  
#         - Use **bullet points** or **numbered lists** for enumerations or key points.  
#         - **Bold** or *italicize* key terms to emphasize important concepts or definitions.

#         3. **Output Formatting**  
#         - Do not create large blocks of text; use **blank lines** to break up sections.  
#         - Ensure the final output is **readable** and well-structured.

#         ---

#         ## Context
#         {context}

#         ## User Question
#         {question}

#         ---

#         ## Helpful Answer:
#         """

#         CUSTOM_PROMPT = PromptTemplate(
#             template=custom_prompt_template, input_variables=["context", "question"]
#         )

#         # Use the retriever from the vector database
#         self.retriever = self.vectordb.as_retriever(search_kwargs={"k": 6})

#         # Create the RetrievalQA chain
#         self.qa = RetrievalQA.from_chain_type(
#             llm=self.llm,
#             chain_type="stuff",
#             retriever=self.retriever,
#             return_source_documents=False,  # Set to False
#             chain_type_kwargs={"prompt": CUSTOM_PROMPT}
#         )

#     def answer_confluence(self,question:str) ->str:
#         """
#         Answer the question
#         """
#         answer = self.qa.run(question)
#         return answer


# @csrf_exempt
# def api_answer(request):
#     if request.method == 'POST':
#         try:
#             # Parse the JSON payload
#             payload = json.loads(request.body)
#             question = payload.get('prompt', None)

#             if not question:
#                 return JsonResponse({'error': 'Prompt is required.'}, status=400)

#             agent = ConfluenceQA()
#             # Initialize embeddings and models if not already done
#             agent.init_embeddings()
#             agent.init_models()
#             agent.vector_db_confluence_docs()  # Ensure the vector database is ready
#             agent.retreival_qa_chain()  # Ensure the QA chain is initialized

#             # Get the answer from the LLM
#             answer = agent.answer_confluence(question)
#             html_answer = markdown.markdown(answer)
#             return HttpResponse(html_answer, content_type="text/html")
#             # return JsonResponse({'answer': answer}, status=200, json_dumps_params={'indent': 4})

#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

#         except Exception as e:
#             # Log the error for debugging
#             print(f"Error in api_answer: {str(e)}")  # Print to console or use logging
#             return JsonResponse({'error': str(e)}, status=500)

#     return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

class ConfluenceQA:
    def __init__(self):
        self.embedding = None
        self.vectordb = None
        self.llm = None
        self.qa = None
        self.retriever = None

    def init_embeddings(self) -> None:
        # Use a higher-quality embedding model
        self.embedding = OpenAIEmbeddings(
            model=EMB_OPENAI_ADA,
            api_key=os.environ["OPENAI_API_KEY"]
        )

    def init_models(self) -> None:
        # Lower temperature for more deterministic answers
        self.llm = ChatOpenAI(
            model_name=LLM_OPENAI_GPT40,
            temperature=0.2
        )

    def vector_db_confluence_docs(self, force_reload: bool = False) -> None:
        """
        Loads documents from Confluence, splits them, and creates/updates a Chroma vector DB.
        """
        persist_directory = os.environ.get("persist_directory", "chroma_db")
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

        # Load existing vector database if available
        if not force_reload and os.path.exists(persist_directory):
            self.vectordb = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embedding
            )
            print("Loaded existing vector database.")
        else:
            self.vectordb = None

        # Identify new space keys that haven't been processed
        new_space_keys = [key for key in space_keys if key not in processed_keys]
        if not new_space_keys:
            print("No new space keys detected. Skipping new embedding.")
            return

        all_documents = []
        for space_key in new_space_keys:
            loader = ConfluenceLoader(
                url=confluence_url,
                username=username,
                api_key=api_key,
                space_key=space_key
            )
            documents = loader.load(limit=400)  # Adjust as needed
            for doc in documents:
                doc.metadata["space_key"] = space_key
            all_documents.extend(documents)
            print(f"Loaded {len(documents)} documents from new space: {space_key}")

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
        if not new_documents:
            print("No new documents to embed.")
            processed_keys.extend(new_space_keys)
            with open(processed_keys_file, "w") as f:
                json.dump(processed_keys, f)
            return

        # Use a recursive text splitter
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        texts = recursive_splitter.split_documents(new_documents)

        if self.vectordb is None:
            self.vectordb = Chroma.from_documents(
                documents=texts,
                embedding=self.embedding,
                persist_directory=persist_directory
            )
            print(f"Created a new vector database with {len(texts)} document chunks.")
        else:
            self.vectordb.add_documents(texts)
            print(f"Added {len(texts)} new document chunks to the existing vector database.")

        processed_keys.extend(new_space_keys)
        with open(processed_keys_file, "w") as f:
            json.dump(processed_keys, f)

    def retreival_qa_chain(self):
        """
        Creates a retrieval QA chain using the 'refine' chain type, specifying that
        the document text is passed as 'context'.
        """

        # This is your custom prompt for the initial response
        question_prompt_template = """You are a Confluence chatbot designed to answer questions about the CZII wiki. Use the provided context to respond accurately and informatively. If you don't know the answer, say that you don't know; do not make up an answer.

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

        # Refine prompt: re-uses the same context instructions but includes `existing_answer`
        # to refine upon. 
        refine_prompt_template = """You are a Confluence chatbot designed to answer questions about the company's wiki.

Below is the **original answer** followed by **additional context**. Refine the original answer to incorporate any new, relevant details from the context. If the new context does not add anything useful, return the original answer.

#         ---

#         ## Original Answer
{existing_answer}

#         ## Additional Context
{context}

#         ## Refined Answer:
"""

        # Build the prompt objects
        question_prompt = PromptTemplate(
            template=question_prompt_template,
            input_variables=["context", "question"]
        )

        refine_prompt = PromptTemplate(
            template=refine_prompt_template,
            input_variables=["existing_answer", "context", "question"]
        )

        # Create the retriever
        self.retriever = self.vectordb.as_retriever(search_kwargs={"k": 6})

        # Use the refine chain
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="refine",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs={
                "question_prompt": question_prompt,
                "refine_prompt": refine_prompt,
                # IMPORTANT: We specify that each document chunk is passed as `context`
                "document_variable_name": "context"
            }
        )

    def answer_confluence(self, question: str) -> str:
        """
        Retrieves relevant chunks and produces an answer for the provided question.
        """
        result = self.qa({"query": question})
        # The final answer is stored under 'result["result"]'
        answer = result.get("result", "")
        return answer


@csrf_exempt
def api_answer(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            question = payload.get('prompt', None)

            if not question:
                return JsonResponse({'error': 'Prompt is required.'}, status=400)

            agent = ConfluenceQA()
            agent.init_embeddings()
            agent.init_models()
            agent.vector_db_confluence_docs()
            agent.retreival_qa_chain()

            answer = agent.answer_confluence(question)
            html_answer = markdown.markdown(answer)
            return HttpResponse(html_answer, content_type="text/html")

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
        except Exception as e:
            print(f"Error in api_answer: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)