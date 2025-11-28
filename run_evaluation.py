#!/usr/bin/env python3
"""
Script untuk menjalankan evaluasi sistem RAG-LLM Assessment Generator.

Script ini digunakan untuk:
1. Mengukur kualitas assessment yang dihasilkan
2. Benchmark performa RAG retrieval
3. Analisis end-to-end sistem
4. Perbandingan dengan baseline (manual)

Penggunaan:
    python run_evaluation.py
    python run_evaluation.py --mode benchmark
    python run_evaluation.py --mode comparison
"""

import argparse
import time
import json
from datetime import datetime

from evaluation.evaluator import EndToEndEvaluator, AssessmentEvaluator
from rag.pipeline import process_files
from rag.retriever import retrieve_context_with_reranking
from rag.embedder import Embedder
from assessment.generator import create_rag_generated_task
from db.connection import get_connection

def evaluate_single_generation(subject_id: int, module_id: int, evaluator: EndToEndEvaluator):
    ...  # kode sama

def run_benchmark(n_samples: int = 5):
    """
    Menjalankan benchmark dengan multiple samples - TETAP BERJALAN meski jumlah modul/subject < n_samples.
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK MODE - Target: {n_samples} Samples (akan dipakai semua modul yang ada)")
    print(f"{'='*60}")
    
    evaluator = EndToEndEvaluator()
    
    # Ambil semua subject yang memiliki modul
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id as module_id, m.subject_id, s.subject
        FROM module m
        JOIN subject s ON m.subject_id = s.id
        ORDER BY m.subject_id ASC, m.id ASC
    """)
    samples = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Ambil hanya sebanyak n_samples jika lebih banyak; jika kurang, gunakan semua
    if not samples:
        print("❌ Tidak ada modul apapun di database untuk diuji (pastikan tabel module dan subject sudah terisi)")
        return
    actual_samples = samples[:n_samples] if len(samples) >= n_samples else samples
    print(f"\nFound {len(actual_samples)} samples to evaluate (dari {len(samples)} modul yang ada di DB)")
    
    results = []
    for i, sample in enumerate(actual_samples, 1):
        print(f"\n\n[Sample {i}/{len(actual_samples)}]")
        result = evaluate_single_generation(
            subject_id=sample['subject_id'],
            module_id=sample['module_id'],
            evaluator=evaluator
        )
        if result:
            results.append(result)
        # Small delay between requests
        if i < len(actual_samples):
            time.sleep(2)
    
    # Print summary
    print(f"\n\n{'='*60}")
    evaluator.print_summary()
    
    # Export report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"evaluation_report_{timestamp}.json"
    evaluator.export_evaluation_report(report_file)
    
    return results

def run_comparison_study():
    ...  # kode sama

def main():
    ...  # kode sama

if __name__ == "__main__":
    main()
