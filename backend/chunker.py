def chunk_text(text, chunk_size=500):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)

    return chunks

if __name__ == '__main__':


    text = """
    Python is a programming language.                                                                              
    It is widely used in artificial intelligence.
    Machine learning uses data to learn patterns.
    Deep learning uses neural networks.
    Natural language processing deals with human language.
    """

    chunks = chunk_text(text, 50)

    for chunk in chunks:
        print("CHUNK:")
        print(chunk)
        print("-" * 30)