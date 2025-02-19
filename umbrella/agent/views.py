import os
from langchain.document_loaders import ConfluenceLoader
from langchain.text_splitter import CharacterTextSplitter, TokenTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain_openai.chat_models.base import BaseChatOpenAI
import markdown
from django.http import HttpResponse


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA

# Constants
EMB_OPENAI_ADA = "text-embedding-ada-002"
EMB_SBERT = None # Chroma takes care

LLM_OPENAI_GPT35 = "gpt-3.5-turbo"
LLM_OPENAI_GPT40_MINI = "gpt-4o-mini"


class ConfluenceQA:
    def __init__(self):

        self.embedding = None
        self.vectordb = None
        self.llm = None
        self.qa = None
        self.retriever = None
    def init_embeddings(self) -> None:
        # OpenAI ada embeddings API
        # self.embedding = OpenAIEmbeddings()
        self.embedding = OpenAIEmbeddings(model="text-embedding-3-small",api_key=os.environ['OPENAI_API_KEY'])
    def init_models(self) -> None:
        # OpenAI GPT 3.5 API
        self.llm = ChatOpenAI(model_name=LLM_OPENAI_GPT40_MINI, temperature=0.)


    def vector_db_confluence_docs(self, force_reload: bool = False) -> None:
        """
        Creates vector db for the embeddings and persists them or loads a vector db from the persist directory
        """
        persist_directory = os.environ.get("persist_directory", "chroma_db")
        confluence_url = os.environ.get("CONFLUENCE_URL", "chroma_db")
        username = os.environ.get("USERNAME", None)
        api_key = os.environ.get("CONFLUENCE_KEY", None)
        space_key = os.environ.get("SPACE_KEY", None)

        if persist_directory and os.path.exists(persist_directory) and not force_reload:
            # Load from the persist db
            self.vectordb = Chroma(persist_directory=persist_directory, embedding_function=self.embedding)
        else:
            # 1. Extract the documents
            loader = ConfluenceLoader(
                url=confluence_url,
                username=username,
                api_key=api_key
            )
            documents = loader.load(
                space_key=space_key,
                limit=400
            )

            # 2. Check for existing embeddings
            existing_embeddings = self.vectordb.get_all_embeddings()  # Assuming this method exists
            existing_ids = {doc['id'] for doc in existing_embeddings}  # Adjust based on your document structure

            # 3. Filter out documents that already exist in the vector db
            new_documents = [doc for doc in documents if doc['id'] not in existing_ids]  # Adjust based on your document structure

            if not new_documents:
                print("No new documents to embed.")
                return  # Exit if there are no new documents

            # 4. Split the texts
            text_splitter = CharacterTextSplitter(chunk_size=20, chunk_overlap=0)
            texts = text_splitter.split_documents(new_documents)
            text_splitter = TokenTextSplitter(chunk_size=100, chunk_overlap=10, encoding_name="cl100k_base")
            texts = text_splitter.split_documents(texts)

            # 5. Create Embeddings and add to chroma store
            self.vectordb = Chroma.from_documents(documents=texts, embedding=self.embedding, persist_directory=persist_directory)

    # def retreival_qa_chain(self):
    #     """
    #     Creates retrieval QA chain using vectordb as retriever and LLM to complete the prompt
    #     """
    #     # Define the custom prompt
    #     custom_prompt_template = """You are a Confluence chatbot answering questions. Use the following pieces of context to answer the question at the end. If you don't know the answer, say that you don't know, don't try to make up an answer.
    #
    #     {context}
    #
    #     Question: {question}
    #     Helpful Answer:"""
    #
    #     CUSTOM_PROMPT = PromptTemplate(
    #         template=custom_prompt_template, input_variables=["context", "question"]
    #     )
    #
    #     # Define a chain type with the custom prompt
    #     from langchain.chains.question_answering import load_qa_chain
    #     from langchain.chains import LLMChain
    #
    #     llm_chain = LLMChain(llm=self.llm, prompt=CUSTOM_PROMPT)
    #     qa_chain = load_qa_chain(llm=self.llm, chain_type="stuff", retriever=self.vectordb.as_retriever())
    #
    #     # Update the QA chain with your custom prompt
    #     self.retriever = self.vectordb.as_retriever(search_kwargs={"k": 4})
    #     self.qa = RetrievalQA(llm_chain=qa_chain, retriever=self.retriever)

    def retreival_qa_chain(self):
        """
        Creates retrieval QA chain using vectordb as retriever and LLM to complete the prompt
        """
        # Define the custom prompt
        custom_prompt_template = """You are a Confluence chatbot designed to answer questions about the company's wiki. Use the provided context to respond accurately and informatively. If you don't know the answer, say that you don't know; do not make up an answer.

        ---

        ## Response Rules

        1. **General Questions (e.g., greetings, navigation, number of wikis, availability)**  
        - Provide a **concise response (under 50 words)**.  
        - Keep the tone **friendly and professional**.  

        2. **Technical or Detailed Queries (e.g., CryoET, pipeline processes, workflows, or research topics)**  
        - Provide a **thorough response (at least 250 words)**.  
        - Use **clear headings** (e.g., "### Introduction", "### Key Details", "### Conclusion").  
        - Separate headings with a **blank line** beneath them for readability.  
        - Use **short paragraphs** (3–5 sentences), and put a **blank line** between paragraphs.  
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

        ## Helpful Answer:
        """

        CUSTOM_PROMPT = PromptTemplate(
            template=custom_prompt_template, input_variables=["context", "question"]
        )

        # Use the retriever from the vector database
        self.retriever = self.vectordb.as_retriever(search_kwargs={"k": 4})

        # Create the RetrievalQA chain
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=False,  # Set to False
            chain_type_kwargs={"prompt": CUSTOM_PROMPT}
        )

    def answer_confluence(self,question:str) ->str:
        """
        Answer the question
        """
        answer = self.qa.run(question)
        return answer


@csrf_exempt
def api_answer(request):
    if request.method == 'POST':
        try:
            # Parse the JSON payload
            payload = json.loads(request.body)
            question = payload.get('prompt', None)

            if not question:
                return JsonResponse({'error': 'Prompt is required.'}, status=400)

            agent = ConfluenceQA()
            # Initialize embeddings and models if not already done
            agent.init_embeddings()
            agent.init_models()
            agent.vector_db_confluence_docs()  # Ensure the vector database is ready
            agent.retreival_qa_chain()  # Ensure the QA chain is initialized

            # Get the answer from the LLM
            answer = agent.answer_confluence(question)
            html_answer = markdown.markdown(answer)
            return HttpResponse(html_answer, content_type="text/html")
            # return JsonResponse({'answer': answer}, status=200, json_dumps_params={'indent': 4})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

        except Exception as e:
            # Log the error for debugging
            print(f"Error in api_answer: {str(e)}")  # Print to console or use logging
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)
