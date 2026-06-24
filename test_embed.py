from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")
emb = model.encode("hello")
print(emb.shape)
