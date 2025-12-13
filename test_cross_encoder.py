# test_cross_encoder.py

from rag.retriever import get_cross_encoder_reranker, retrieve_context_with_reranking
from rag.embedder import Embedder
from rag.vectorstore import VectorStore
import sys

def test_cross_encoder():
    """Test CrossEncoder loading and basic functionality."""
    print("=== Testing CrossEncoder Reranker ===")

    # Test 1: Load CrossEncoder
    print("\n1. Loading CrossEncoder...")
    reranker = get_cross_encoder_reranker()

    if reranker and reranker.is_available():
        print("SUCCESS: CrossEncoder loaded successfully!")
        print(f"Model: {reranker.model_name}")
    else:
        print("WARNING: CrossEncoder not available")
        return False

    # Test 2: Basic reranking functionality
    print("\n2. Testing reranking functionality...")
    query = "conditional statements in Python"
    documents = [
        "Python if-else statements allow conditional execution",
        "Loops are used for iteration in programming",
        "Functions are reusable code blocks",
        "Variables store data values",
        "Lists are mutable data structures in Python"
    ]

    results = reranker.rerank(query, documents, top_k=3)

    print(f"Query: {query}")
    print("Reranked results:")
    for i, result in enumerate(results):
        print(f"  {i+1}. Score: {result['score']:.4f} - {result['text'][:60]}...")

    # Test 3: Integration with RAG pipeline
    print("\n3. Testing RAG pipeline integration...")
    try:
        # Initialize components
        embedder = Embedder()
        vectorstore = VectorStore(embedder.get_embedding_dimension())

        # Add some test data
        test_docs = [
            "Python if statement checks a condition and executes code if true",
            "Python for loop iterates over a sequence of elements",
            "Python while loop continues as long as condition is true",
            "Python function defined with def keyword",
            "Python variable assignment using equals sign"
        ]

        for doc in test_docs:
            embedding = embedder.encode([doc])
            vectorstore.add(embedding[0], doc, {"test": True})

        # Test retrieval with CrossEncoder reranking
        context_results = retrieve_context_with_reranking(
            vectorstore=vectorstore,
            embedder=embedder,
            query="conditional statements in Python",
            top_k=3,
            initial_k=5
        )

        print(f"Retrieved {len(context_results)} contexts with CrossEncoder reranking:")
        for i, ctx in enumerate(context_results):
            has_rerank = 'rerank_score' in ctx
            score_info = f"Original: {ctx.get('original_score', 0):.3f}"
            if has_rerank:
                score_info += f" -> Reranked: {ctx.get('rerank_score', 0):.3f}"
            print(f"  {i+1}. {score_info}")
            print(f"     {ctx.get('text', '')[:80]}...")

        print("\nSUCCESS: CrossEncoder integration working!")
        return True

    except Exception as e:
        print(f"ERROR: RAG integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_cross_encoder()
    if success:
        print("\nSUCCESS: All CrossEncoder tests passed!")
    else:
        print("\nERROR: Some tests failed!")
    sys.exit(0 if success else 1)