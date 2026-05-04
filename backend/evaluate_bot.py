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

import time
from datetime import datetime

# Expanded to 10 questions to meet assignment requirements
TEST_QUESTIONS = [
    "What is Acibadem University?",
    "Tell me about the Computer Engineering program.",
    "What are the admission requirements?",
    "Where is the campus located?",
    "Can you give information about campus life and student clubs?",
    "Who is the rector of the university?",
    "What kind of facilities does the library have?",
    "How many faculties and schools are there?",
    "Are there any scholarship opportunities for international students?",
    "What health services are available for students on campus?"
]

def generate_markdown_report(results, total_duration):
    report_path = "evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# ACU Chatbot RAG Evaluation Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Questions:** {len(results)}\n")
        f.write(f"**Total Evaluation Time:** {total_duration:.2f} seconds\n\n")
        f.write("---\n\n")

        for idx, res in enumerate(results, start=1):
            f.write(f"## Q{idx}: {res['question']}\n\n")
            if res.get('error'):
                f.write(f"**Error:** `{res['error']}`\n\n")
                continue
            
            f.write(f"**Response Time:** `{res['duration']:.2f}s`\n\n")
            f.write(f"**Answer:**\n{res['answer']}\n\n")
            
            f.write(f"### Sources Used ({len(res.get('sources', []))} found)\n")
            for s_idx, src in enumerate(res.get('sources', []), start=1):
                f.write(f"{s_idx}. [{src.get('title', 'Unknown')}]({src.get('url', '#')})\n")
            f.write("\n---\n\n")
    return report_path

def run_full_evaluation():
    print("=" * 60)
    print("🤖 Starting Comprehensive RAG Evaluation")
    print(f"Total Questions to Process: {len(TEST_QUESTIONS)}")
    print("=" * 60)
    
    results = []
    start_total = time.time()
    
    for idx, question in enumerate(TEST_QUESTIONS, start=1):
        print(f"\n[{idx}/{len(TEST_QUESTIONS)}] Processing: '{question}'...")
        
        start_q = time.time()
        try_result = {
            "question": question,
        }
        try:
            result = generate_chat_answer(question)
            duration = time.time() - start_q
            
            try_result.update({
                "answer": result.get('answer', ''),
                "sources": result.get('sources', []),
                "duration": duration,
                "status": "success"
            })
            print(f" ✓ Success! ({duration:.2f}s) | Sources: {len(result.get('sources', []))}")
            
        except Exception as e:
            duration = time.time() - start_q
            try_result.update({
                "error": str(e),
                "duration": duration,
                "status": "failed"
            })
            print(f" ✗ Failed! ({duration:.2f}s) | Error: {str(e)}")
            
        results.append(try_result)
    
    total_duration = time.time() - start_total
    print("\n" + "=" * 60)
    print(f"Evaluation finished in {total_duration:.2f}s.")
    print("Generating Markdown report...")
    
    report_file = generate_markdown_report(results, total_duration)
    print(f"✓ Report successfully saved to: {report_file}")

if __name__ == "__main__":
    run_full_evaluation()
