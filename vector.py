from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

def text_splitter(data: list, chunk_size: int = 1000, chunk_overlap: int = 100, is_separator_regex: bool = False):
    """function text_splitter
    parameter:
        data: list (require)
        chunk_size: int (require)
        chunk_overlap: int (require)
        is_separator_regex: bool (optional)"""
    
    if type(data) != list:
        return f"Type Error: Expect list type, not {type(data)}"
    elif type(chunk_size) != int:
        return f"Type Error: Expect int type, not {type(chunk_size)}"
    elif type(chunk_overlap) != int:
        return f"Type Error: Expect int type, not {type(chunk_overlap)}"
    elif type(is_separator_regex) != bool:
        return f"Type Error: Expect bool type, not {type(is_separator_regex)}"
    
    _text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=is_separator_regex
    )
    
    texts = _text_splitter.create_documents(data)
    
    return texts

def vectors(directory: str, collection_name: str, data: list = [], new: bool = False):
    """function create_vector
    parameter:
        data: list (require)
        directory: str (require)
        collection_name: str (require)
        new: bool (optional)"""
    
    if type(data) != list:
        return f"Type Error: Expect list type, not {type(data)}"
    elif type(directory) != str:
        return f"Type Error: Expect str type, not {type(directory)}"
    elif type(new) != bool:
        return f"Type Error: Expect bool type, not {type(new)}"
    
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=OpenAIEmbeddings(),
        persist_directory=directory
    )
    
    if new != False:
        vector_store.add_documents(documents=data)
    
    return vector_store



# # Load example document
# with open("C:\\Users\\hookj\\Desktop\\17-5-68 nuV\\server\\RAG2.txt",encoding="utf-8") as f:
#     state_of_the_union = f.read()
    
# a = text_splitter(
#     data=[state_of_the_union],
#     is_separator_regex=True
# )

# vectors(
#     directory="./vectorDB",
#     collection_name="vector",
#     data=a,
#     new=True
    
# )