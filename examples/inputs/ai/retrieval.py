from langchain_core.runnables import RunnableLambda
from langchain.retrievers import MultiQueryRetriever

def build_answer_chain(retriever: MultiQueryRetriever, model):
    def generate(question):
        documents = retriever.invoke(question)
        return model.invoke({"question": question, "context": documents})
    return RunnableLambda(generate)
