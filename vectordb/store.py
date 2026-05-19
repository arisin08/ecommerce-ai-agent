
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from langchain_core.documents import Document
from langchain_chroma import Chroma
from core.database import AsyncSessionLocal, Product
from config import CHROMA_DIR
from pathlib import Path

#embeddings model
embedder = OpenAIEmbeddings(model = 'text-embedding-3-small')

inventory_agent_db = None
inventory_agent_search = None  

async def build_vector_store():
    global inventory_agent_db,  inventory_agent_search 

        # load from disk if already exists
    if Path(CHROMA_DIR).exists():
        inventory_agent_db = Chroma(
            collection_name="store_inventory",
            embedding_function=embedder,
            persist_directory=CHROMA_DIR
        )
        inventory_agent_search = inventory_agent_db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.2}
        )
        print("########### Vector Store Loaded From Disk #########")
        return 
        
    #creating document list for injection into Chroma DB
    processed_docs = []

    async with AsyncSessionLocal() as session:
        

        result = await session.execute(select(Product))
        products = result.scalars().all()
            
        for p in products:
            data = p.name + " " + p.category + " " + p.description + " " + str(p.unit_price)
            metadata = {"product_id" : p.id,
                        "name" : p.name,
                        "category" : p.category,
                        "unit_price" : p.unit_price,
                        "quantity" : p.quantity
                        }

            processed_docs.append(Document(page_content=data, metadata=metadata))


        #creating vector store (ChromaDB)
        inventory_agent_db = Chroma.from_documents(documents = processed_docs,
                                                collection_name = 'store_inventory',
                                                embedding = embedder,
                                                collection_metadata = {'hnsw:space' : 'cosine'},
                                                persist_directory = CHROMA_DIR)

        #creating retriever
        inventory_agent_search = inventory_agent_db.as_retriever(search_type = "similarity_score_threshold", 
                                                                    search_kwargs = {"k":3, "score_threshold": 0.2})
        
        print("########### Vector Store Established #########")

def semantic_search(query:str):
    result = inventory_agent_search.invoke(query)
    return [doc.metadata for doc in result]





