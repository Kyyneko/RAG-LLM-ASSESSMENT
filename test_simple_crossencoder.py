# test_simple_crossencoder.py

from rag.retriever import get_cross_encoder_reranker

def test_crossencoder_simple():
    """Simple test for CrossEncoder loading and basic functionality."""
    print("=== CrossEncoder Reranker Test ===")

    try:
        # Load reranker
        print("1. Loading CrossEncoder...")
        reranker = get_cross_encoder_reranker()

        if reranker and reranker.is_available():
            print(f"SUCCESS: CrossEncoder loaded!")
            print(f"Model: {reranker.model_name}")

            # Test basic reranking
            print("\n2. Testing reranking...")
            query = "Python programming conditional statements"
            docs = [
                "Python if-else statements allow conditional execution of code blocks",
                "Python for loops are used for iteration over sequences",
                "Python functions are reusable code blocks with parameters",
                "Python variables store data values of different types",
                "Python lists are mutable ordered collections"
            ]

            results = reranker.rerank(query, docs, top_k=3)

            print(f"Query: {query}")
            print(f"Top {len(results)} results:")
            for i, result in enumerate(results):
                print(f"  {i+1}. Score: {result['score']:.4f} | {result['text'][:50]}...")

            print("\nSUCCESS: CrossEncoder reranking working!")
            return True
        else:
            print("ERROR: CrossEncoder not available")
            return False

    except Exception as e:
        print(f"ERROR: Test failed - {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_crossencoder_simple()
    if success:
        print("\nSUCCESS: CrossEncoder implementation SUCCESS!")
    else:
        print("\nERROR: CrossEncoder implementation FAILED!")