#!/usr/bin/env python
"""
Automated Model Evaluation Script (Part 1 - Skeleton and Questions)
This script initializes Django and prepares the test suite for the RAG model.
"""
import os
import sys

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chatbot.settings")

import django
django.setup()

from rag.api_views import generate_chat_answer

# A diverse set of questions to test knowledge retrieval and generation
# These cover general info, academic programs, admission, and campus life.
TEST_QUESTIONS = [
    "What is Acibadem University?",
    "Tell me about the Computer Engineering program.",
    "What are the admission requirements?",
    "Where is the campus located?",
    "Can you give information about campus life and student clubs?"
]

def run_basic_evaluation():
    print("=" * 60)
    print("🤖 RAG Model Basic Evaluation Starter")
    print("=" * 60)
    
    for idx, question in enumerate(TEST_QUESTIONS, start=1):
        print(f"\n[{idx}/{len(TEST_QUESTIONS)}] Question: {question}")
        try:
            # We simply call the model here to check if the pipeline works.
            # In the next step, we will add timing, metric tracking, and reporting.
            result = generate_chat_answer(question)
            answer_preview = result.get('answer', '').replace('\n', ' ')[:100]
            print(f"Answer Preview: {answer_preview}...")
            print(f"Sources Found: {len(result.get('sources', []))}")
        except Exception as e:
            print(f"Error asking question: {str(e)}")

if __name__ == "__main__":
    run_basic_evaluation()
