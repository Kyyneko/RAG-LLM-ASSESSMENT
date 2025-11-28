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
    """
    Evaluasi satu kali generasi assessment.
    """
    print(f"\n{'='*60}")
    print(f"Evaluating Generation: Subject {subject_id}, Module {module_id}")
    print(f"{'='*60}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get subject info
        cursor.execute("SELECT id, subject FROM subject WHERE id = %s", (subject_id,))
        subject = cursor.fetchone()
        
        if not subject:
            print(f"❌ Subject {subject_id} not found")
            return None
        
        subject_name = subject["subject"]
        
        # Get module info
        cursor.execute(
            "SELECT id, title, file_path, session_id FROM module WHERE id = %s",
            (module_id,)
        )
        module = cursor.fetchone()
        
        if not module:
            print(f"❌ Module {module_id} not found")
            return None
        
        module_title = module["title"]
        file_path = module["file_path"]
        session_id = module["session_id"]
        
        # Get session info
        cursor.execute(
            "SELECT topic, class_id FROM session WHERE id = %s",
            (session_id,)
        )
        session = cursor.fetchone()
        topic = session["topic"] if session else module_title
        
        print(f"\n[Input]")
        print(f"  Subject: {subject_name}")
        print(f"  Topic: {topic}")
        print(f"  Module: {module_title}")
        print(f"  File: {file_path}")
        
        # START TIMING
        total_start = time.time()
        
        # 1. RAG Retrieval
        print(f"\n[Step 1] RAG Retrieval...")
        retrieval_start = time.time()
        
        embedder = Embedder()
        vectorstore = process_files([file_path], embedder)
        
        query = f"Materi praktikum tentang {topic} dalam mata kuliah {subject_name}"
        context_snippets = retrieve_context_with_reranking(
            vectorstore=vectorstore,
            embedder=embedder,
            query=query,
            top_k=5,
            initial_k=15
        )
        
        retrieval_time = time.time() - retrieval_start
        print(f"  ✓ Retrieved {len(context_snippets)} contexts in {retrieval_time:.2f}s")
        
        # 2. LLM Generation
        print(f"\n[Step 2] LLM Generation...")
        generation_start = time.time()
        
        from llm.generator import generate_assessment_description
        generated_text = generate_assessment_description(
            subject_name=subject_name,
            topic=topic,
            class_name="Test",
            context_snippets=context_snippets
        )
        
        generation_time = time.time() - generation_start
        total_time = time.time() - total_start
        
        print(f"  ✓ Generated {len(generated_text)} characters in {generation_time:.2f}s")
        print(f"  ✓ Total time: {total_time:.2f}s")
        
        # 3. Evaluation
        print(f"\n[Step 3] Evaluation...")
        result = evaluator.evaluate_generation_pipeline(
            subject_name=subject_name,
            topic=topic,
            module_file=file_path,
            generated_assessment=generated_text,
            retrieval_time=retrieval_time,
            generation_time=generation_time,
            total_time=total_time,
            context_snippets=[c if isinstance(c, str) else c.get('text', '') for c in context_snippets]
        )
        
        # Print results
        print(f"\n[Results]")
        print(f"  Overall Score: {result['assessment_quality']['overall_score']:.2f}/100")
        print(f"  Structural Completeness: {result['assessment_quality']['structural_completeness']['completeness_score']:.1f}%")
        print(f"  Content Quality: {result['assessment_quality']['content_quality']['quality_score']:.1f}/100")
        
        return result
        
    finally:
        cursor.close()
        conn.close()


def run_benchmark(n_samples: int = 5):
    """
    Menjalankan benchmark dengan multiple samples.
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK MODE - {n_samples} Samples")
    print(f"{'='*60}")
    
    evaluator = EndToEndEvaluator()
    
    # Get sample data from database
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT m.id as module_id, m.subject_id, s.subject
        FROM module m
        JOIN subject s ON m.subject_id = s.id
        LIMIT %s
    """, (n_samples,))
    
    samples = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not samples:
        print("❌ No samples found in database")
        return
    
    print(f"\nFound {len(samples)} samples to evaluate")
    
    results = []
    for i, sample in enumerate(samples, 1):
        print(f"\n\n[Sample {i}/{len(samples)}]")
        result = evaluate_single_generation(
            subject_id=sample['subject_id'],
            module_id=sample['module_id'],
            evaluator=evaluator
        )
        if result:
            results.append(result)
        
        # Small delay between requests
        if i < len(samples):
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
    """
    Menjalankan studi perbandingan dengan baseline.
    
    Baseline: Manual assessment creation (data dari database yang dibuat manual)
    Experimental: RAG-LLM generated assessment
    """
    print(f"\n{'='*60}")
    print(f"COMPARISON STUDY: RAG-LLM vs Manual Baseline")
    print(f"{'='*60}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get manual assessments (baseline)
    cursor.execute("""
        SELECT id, description, created_at
        FROM assessment_task
        WHERE source_type = 'manual'
        LIMIT 10
    """)
    manual_assessments = cursor.fetchall()
    
    # Get RAG-generated assessments
    cursor.execute("""
        SELECT id, description, ai_generated_description, created_at
        FROM assessment_task
        WHERE source_type = 'rag_generated'
        LIMIT 10
    """)
    rag_assessments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Evaluate both
    evaluator = AssessmentEvaluator()
    
    manual_scores = []
    rag_scores = []
    
    print(f"\n[Evaluating Manual Baseline]")
    for i, assessment in enumerate(manual_assessments, 1):
        result = evaluator.evaluate_assessment(
            assessment['description'],
            metadata={'type': 'manual', 'id': assessment['id']}
        )
        manual_scores.append(result['overall_score'])
        print(f"  [{i}] Score: {result['overall_score']:.2f}")
    
    print(f"\n[Evaluating RAG-Generated]")
    for i, assessment in enumerate(rag_assessments, 1):
        result = evaluator.evaluate_assessment(
            assessment['ai_generated_description'] or assessment['description'],
            metadata={'type': 'rag', 'id': assessment['id']}
        )
        rag_scores.append(result['overall_score'])
        print(f"  [{i}] Score: {result['overall_score']:.2f}")
    
    # Statistical comparison
    print(f"\n{'='*60}")
    print(f"COMPARISON RESULTS")
    print(f"{'='*60}")
    
    if manual_scores:
        print(f"\n[Manual Baseline]")
        print(f"  Count: {len(manual_scores)}")
        print(f"  Mean Score: {sum(manual_scores)/len(manual_scores):.2f}")
        print(f"  Min: {min(manual_scores):.2f}")
        print(f"  Max: {max(manual_scores):.2f}")
    
    if rag_scores:
        print(f"\n[RAG-LLM System]")
        print(f"  Count: {len(rag_scores)}")
        print(f"  Mean Score: {sum(rag_scores)/len(rag_scores):.2f}")
        print(f"  Min: {min(rag_scores):.2f}")
        print(f"  Max: {max(rag_scores):.2f}")
    
    if manual_scores and rag_scores:
        improvement = ((sum(rag_scores)/len(rag_scores)) - (sum(manual_scores)/len(manual_scores)))
        print(f"\n[Improvement]")
        print(f"  Difference: {improvement:+.2f} points")
        print(f"  Relative: {improvement/(sum(manual_scores)/len(manual_scores))*100:+.1f}%")
    
    # Export
    comparison_data = {
        "timestamp": datetime.now().isoformat(),
        "manual_baseline": {
            "scores": manual_scores,
            "mean": sum(manual_scores)/len(manual_scores) if manual_scores else 0
        },
        "rag_system": {
            "scores": rag_scores,
            "mean": sum(rag_scores)/len(rag_scores) if rag_scores else 0
        }
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"comparison_study_{timestamp}.json", 'w') as f:
        json.dump(comparison_data, f, indent=2)
    
    print(f"\n✓ Comparison data exported")


def main():
    parser = argparse.ArgumentParser(description="RAG-LLM System Evaluation")
    parser.add_argument(
        '--mode',
        choices=['single', 'benchmark', 'comparison'],
        default='single',
        help='Evaluation mode'
    )
    parser.add_argument(
        '--subject-id',
        type=int,
        default=1,
        help='Subject ID for single evaluation'
    )
    parser.add_argument(
        '--module-id',
        type=int,
        default=2,
        help='Module ID for single evaluation'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=5,
        help='Number of samples for benchmark'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        evaluator = EndToEndEvaluator()
        evaluate_single_generation(args.subject_id, args.module_id, evaluator)
        evaluator.print_summary()
        
    elif args.mode == 'benchmark':
        run_benchmark(args.samples)
        
    elif args.mode == 'comparison':
        run_comparison_study()


if __name__ == "__main__":
    main()
