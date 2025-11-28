# evaluation/evaluator.py
"""
Modul Evaluasi untuk Sistem RAG-LLM Assessment Generator

Modul ini mengukur efektivitas sistem dalam:
1. Kualitas soal yang dihasilkan
2. Relevansi konteks retrieval
3. Performa dan efisiensi sistem
4. Perbandingan dengan baseline
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Tuple
import re


class AssessmentEvaluator:
    """
    Evaluator untuk mengukur kualitas assessment yang dihasilkan.
    """
    
    def __init__(self):
        self.metrics_history = []
    
    def evaluate_assessment(self, generated_text: str, metadata: Dict = None) -> Dict:
        """
        Evaluasi komprehensif untuk assessment yang dihasilkan.
        
        Args:
            generated_text: Teks assessment yang dihasilkan LLM
            metadata: Informasi tambahan (subject, topic, dll)
        
        Returns:
            Dict berisi berbagai metrics
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            
            # 1. Structural Completeness
            "structural_completeness": self._check_structure(generated_text),
            
            # 2. Content Quality
            "content_quality": self._assess_content_quality(generated_text),
            
            # 3. Length Metrics
            "length_metrics": self._calculate_length_metrics(generated_text),
            
            # 4. Technical Requirements
            "technical_requirements": self._check_technical_requirements(generated_text),
            
            # 5. Overall Score
            "overall_score": 0.0
        }
        
        # Calculate overall score
        metrics["overall_score"] = self._calculate_overall_score(metrics)
        
        # Store in history
        self.metrics_history.append(metrics)
        
        return metrics
    
    def _check_structure(self, text: str) -> Dict:
        """
        Memeriksa kelengkapan struktur assessment (tags).
        """
        required_tags = ["#SOAL", "#REQUIREMENTS", "#EXPECTED OUTPUT", "#KUNCI JAWABAN"]
        
        structure = {
            "has_all_tags": True,
            "missing_tags": [],
            "tag_positions": {},
            "completeness_score": 0.0
        }
        
        for tag in required_tags:
            if tag in text:
                # Find position of tag
                pos = text.find(tag)
                structure["tag_positions"][tag] = pos
            else:
                structure["has_all_tags"] = False
                structure["missing_tags"].append(tag)
        
        # Calculate completeness score
        found_tags = len(required_tags) - len(structure["missing_tags"])
        structure["completeness_score"] = (found_tags / len(required_tags)) * 100
        
        return structure
    
    def _assess_content_quality(self, text: str) -> Dict:
        """
        Mengukur kualitas konten assessment.
        """
        quality = {
            "has_code_block": "```" in text,
            "has_requirements_list": bool(re.search(r'\d+\.\s+', text)),
            "has_indonesian_text": bool(re.search(r'[a-zA-Z]+', text)),
            "code_blocks_count": text.count('```') // 2,
            "requirements_count": len(re.findall(r'\n\d+\.\s+', text)),
            "quality_score": 0.0
        }
        
        # Calculate quality score
        score = 0
        if quality["has_code_block"]: score += 30
        if quality["has_requirements_list"]: score += 20
        if quality["has_indonesian_text"]: score += 20
        if quality["code_blocks_count"] >= 1: score += 15
        if quality["requirements_count"] >= 3: score += 15
        
        quality["quality_score"] = min(score, 100)
        
        return quality
    
    def _calculate_length_metrics(self, text: str) -> Dict:
        """
        Menghitung metrik panjang teks.
        """
        return {
            "total_characters": len(text),
            "total_words": len(text.split()),
            "total_lines": len(text.split('\n')),
            "code_characters": self._count_code_characters(text)
        }
    
    def _count_code_characters(self, text: str) -> int:
        """
        Menghitung jumlah karakter dalam code block.
        """
        code_blocks = re.findall(r'```.*?```', text, re.DOTALL)
        return sum(len(block) for block in code_blocks)
    
    def _check_technical_requirements(self, text: str) -> Dict:
        """
        Memeriksa keberadaan elemen teknis.
        """
        return {
            "has_input_output": "input" in text.lower() or "output" in text.lower(),
            "has_variables": bool(re.search(r'[a-zA-Z_][a-zA-Z0-9_]*\s*=', text)),
            "has_comments": "#" in text and "#SOAL" not in text,  # Python comments
            "has_print_statement": "print" in text.lower(),
        }
    
    def _calculate_overall_score(self, metrics: Dict) -> float:
        """
        Menghitung skor keseluruhan dari berbagai metrics.
        """
        # Weighted scoring
        weights = {
            "structure": 0.3,
            "quality": 0.4,
            "technical": 0.3
        }
        
        structure_score = metrics["structural_completeness"]["completeness_score"]
        quality_score = metrics["content_quality"]["quality_score"]
        
        # Technical score
        tech = metrics["technical_requirements"]
        tech_score = sum([
            tech["has_input_output"] * 25,
            tech["has_variables"] * 25,
            tech["has_comments"] * 25,
            tech["has_print_statement"] * 25
        ])
        
        overall = (
            structure_score * weights["structure"] +
            quality_score * weights["quality"] +
            tech_score * weights["technical"]
        )
        
        return round(overall, 2)
    
    def get_summary_statistics(self) -> Dict:
        """
        Mendapatkan statistik ringkasan dari semua evaluasi.
        """
        if not self.metrics_history:
            return {"error": "No evaluation data available"}
        
        scores = [m["overall_score"] for m in self.metrics_history]
        completeness = [m["structural_completeness"]["completeness_score"] 
                       for m in self.metrics_history]
        
        return {
            "total_evaluations": len(self.metrics_history),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "average_completeness": sum(completeness) / len(completeness),
            "success_rate": sum(1 for s in scores if s >= 70) / len(scores) * 100
        }


class RAGPerformanceEvaluator:
    """
    Evaluator untuk mengukur performa sistem RAG.
    """
    
    def __init__(self):
        self.performance_logs = []
    
    def measure_retrieval_performance(
        self, 
        query: str, 
        retrieved_contexts: List[str],
        ground_truth_contexts: List[str] = None,
        execution_time: float = None
    ) -> Dict:
        """
        Mengukur performa retrieval.
        
        Args:
            query: Query pencarian
            retrieved_contexts: Konteks yang di-retrieve
            ground_truth_contexts: Konteks yang seharusnya (optional)
            execution_time: Waktu eksekusi retrieval
        
        Returns:
            Dict metrics performa
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "retrieved_count": len(retrieved_contexts),
            "execution_time_seconds": execution_time,
            "average_context_length": sum(len(c) for c in retrieved_contexts) / len(retrieved_contexts) if retrieved_contexts else 0,
        }
        
        # Jika ada ground truth, hitung precision/recall
        if ground_truth_contexts:
            metrics["precision_recall"] = self._calculate_precision_recall(
                retrieved_contexts, 
                ground_truth_contexts
            )
        
        self.performance_logs.append(metrics)
        return metrics
    
    def _calculate_precision_recall(
        self, 
        retrieved: List[str], 
        ground_truth: List[str]
    ) -> Dict:
        """
        Menghitung precision dan recall (simplified).
        """
        # Simple text overlap based
        relevant_retrieved = 0
        for ret in retrieved:
            for gt in ground_truth:
                if self._text_overlap(ret, gt) > 0.5:  # 50% overlap threshold
                    relevant_retrieved += 1
                    break
        
        precision = relevant_retrieved / len(retrieved) if retrieved else 0
        recall = relevant_retrieved / len(ground_truth) if ground_truth else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3)
        }
    
    def _text_overlap(self, text1: str, text2: str) -> float:
        """
        Menghitung overlap antara dua teks.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def get_performance_summary(self) -> Dict:
        """
        Mendapatkan ringkasan performa.
        """
        if not self.performance_logs:
            return {"error": "No performance data available"}
        
        times = [log["execution_time_seconds"] for log in self.performance_logs 
                if log["execution_time_seconds"] is not None]
        
        summary = {
            "total_retrievals": len(self.performance_logs),
            "average_retrieval_time": sum(times) / len(times) if times else None,
            "min_retrieval_time": min(times) if times else None,
            "max_retrieval_time": max(times) if times else None,
        }
        
        # Calculate average precision/recall if available
        pr_logs = [log for log in self.performance_logs if "precision_recall" in log]
        if pr_logs:
            precisions = [log["precision_recall"]["precision"] for log in pr_logs]
            recalls = [log["precision_recall"]["recall"] for log in pr_logs]
            f1s = [log["precision_recall"]["f1_score"] for log in pr_logs]
            
            summary["average_precision"] = sum(precisions) / len(precisions)
            summary["average_recall"] = sum(recalls) / len(recalls)
            summary["average_f1_score"] = sum(f1s) / len(f1s)
        
        return summary


class EndToEndEvaluator:
    """
    Evaluator untuk mengukur performa end-to-end sistem.
    """
    
    def __init__(self):
        self.assessment_evaluator = AssessmentEvaluator()
        self.rag_evaluator = RAGPerformanceEvaluator()
        self.e2e_logs = []
    
    def evaluate_generation_pipeline(
        self,
        subject_name: str,
        topic: str,
        module_file: str,
        generated_assessment: str,
        retrieval_time: float,
        generation_time: float,
        total_time: float,
        context_snippets: List[str]
    ) -> Dict:
        """
        Evaluasi end-to-end dari proses generasi.
        
        Returns:
            Dict berisi semua metrics
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "input": {
                "subject": subject_name,
                "topic": topic,
                "module": module_file
            },
            "timing": {
                "retrieval_time_seconds": retrieval_time,
                "generation_time_seconds": generation_time,
                "total_time_seconds": total_time
            },
            "assessment_quality": self.assessment_evaluator.evaluate_assessment(
                generated_assessment,
                metadata={"subject": subject_name, "topic": topic}
            ),
            "rag_performance": self.rag_evaluator.measure_retrieval_performance(
                query=f"{subject_name} - {topic}",
                retrieved_contexts=context_snippets,
                execution_time=retrieval_time
            )
        }
        
        self.e2e_logs.append(result)
        return result
    
    def export_evaluation_report(self, filepath: str = "evaluation_report.json"):
        """
        Export hasil evaluasi ke file JSON.
        """
        report = {
            "report_generated_at": datetime.now().isoformat(),
            "assessment_summary": self.assessment_evaluator.get_summary_statistics(),
            "rag_summary": self.rag_evaluator.get_performance_summary(),
            "detailed_logs": self.e2e_logs
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Evaluation report exported to: {filepath}")
        return report
    
    def print_summary(self):
        """
        Print ringkasan evaluasi ke console.
        """
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)
        
        # Assessment Quality Summary
        ass_summary = self.assessment_evaluator.get_summary_statistics()
        if "error" not in ass_summary:
            print("\n[Assessment Quality]")
            print(f"  Total Evaluations: {ass_summary['total_evaluations']}")
            print(f"  Average Score: {ass_summary['average_score']:.2f}/100")
            print(f"  Success Rate (≥70): {ass_summary['success_rate']:.1f}%")
        
        # RAG Performance Summary
        rag_summary = self.rag_evaluator.get_performance_summary()
        if "error" not in rag_summary:
            print("\n[RAG Performance]")
            print(f"  Total Retrievals: {rag_summary['total_retrievals']}")
            if rag_summary.get('average_retrieval_time'):
                print(f"  Avg Retrieval Time: {rag_summary['average_retrieval_time']:.2f}s")
            if rag_summary.get('average_f1_score'):
                print(f"  Avg F1 Score: {rag_summary['average_f1_score']:.3f}")
        
        print("\n" + "="*60 + "\n")
