from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(text, chunk_size=512, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
    )
    raw_chunks = splitter.split_text(text)
    chunks = []
    for chunk in raw_chunks:
        stripped = chunk.strip()
        if len(stripped) >= 50:
            chunks.append(chunk)
    return chunks
