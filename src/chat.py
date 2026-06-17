import sys
import os

# Ensure src/ is on sys.path regardless of where the script is invoked from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from retriever import Retriever


def chat():

    print("\nYantra RAG Chat")
    print("Type 'exit' to quit\n")

    retriever = Retriever()

    while True:

        question = input("\nYou: ")

        if question.lower() == "exit":
            break

        # Trigger the Agentic Workflow
        print("\n[System] Thinking (Agentic RAG Pipeline)...")
        answer = retriever.ask(question)

        print("\n============================================")
        print("OWL ALPHA ANSWER")
        print("============================================")
        print(f"\n{answer}\n")
        print("============================================")


if __name__ == "__main__":
    chat()