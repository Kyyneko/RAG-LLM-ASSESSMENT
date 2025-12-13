# db/generation_logger.py

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .connection import get_connection

logger = logging.getLogger(__name__)


class AIGenerationLogger:
    """
    Logger untuk mencatat semua proses generasi AI assessment.

    Fungsi:
    - Log setiap request generasi ke database
    - Track status: pending, success, failed
    - Store parameters, context, dan hasil
    - Monitor performance dan error tracking
    """

    def __init__(self):
        self.logger = logger

    def log_generation_request(
        self,
        assessment_task_id: Optional[int],
        generation_type: str,
        prompt_parameters: Dict[str, Any],
        source_materials: Optional[Dict[str, Any]],
        model_used: str,
        generated_by: Optional[int] = None
    ) -> int:
        """
        Log request generasi baru ke database.

        Args:
            assessment_task_id: ID assessment task (optional)
            generation_type: Tipe generasi ('assessment', 'preview', etc)
            prompt_parameters: Parameter prompt (subject, topic, context, etc)
            source_materials: Source materials yang digunakan (modules, chunks)
            model_used: Model LLM yang digunakan
            generated_by: ID user yang melakukan request

        Returns:
            int: ID dari record yang dibuat
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO ai_generation_log
                (assessment_task_id, generation_type, prompt_parameters,
                 source_materials, model_used, generation_status, generated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                assessment_task_id,
                generation_type,
                json.dumps(prompt_parameters, default=str),
                json.dumps(source_materials, default=str),
                model_used,
                'pending',
                generated_by
            ))

            generation_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Generation request logged: ID {generation_id}, Type: {generation_type}")
            return generation_id

        except Exception as e:
            logger.error(f"Error logging generation request: {str(e)}")
            raise

    def update_generation_success(
        self,
        generation_id: int,
        generated_content: str,
        execution_time_ms: Optional[int] = None
    ):
        """
        Update log ketika generasi berhasil.

        Args:
            generation_id: ID dari generation log
            generated_content: Content yang berhasil digenerate
            execution_time_ms: Waktu eksekusi dalam milliseconds
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Update status dan content
            update_query = """
                UPDATE ai_generation_log
                SET generation_status = 'success',
                    generated_content = %s
                WHERE id = %s
            """
            params = [generated_content, generation_id]

            # Add execution time if provided
            if execution_time_ms is not None:
                # Add execution time to prompt_parameters
                cursor.execute("SELECT prompt_parameters FROM ai_generation_log WHERE id = %s", (generation_id,))
                result = cursor.fetchone()
                if result and result['prompt_parameters']:
                    prompt_params = json.loads(result['prompt_parameters'])
                    prompt_params['execution_time_ms'] = execution_time_ms

                    update_query = """
                        UPDATE ai_generation_log
                        SET generation_status = 'success',
                            generated_content = %s,
                            prompt_parameters = %s
                        WHERE id = %s
                    """
                    params = [generated_content, json.dumps(prompt_params, default=str), generation_id]

            cursor.execute(update_query, params)
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Generation success logged: ID {generation_id}")

        except Exception as e:
            logger.error(f"Error updating generation success: {str(e)}")
            raise

    def update_generation_error(
        self,
        generation_id: int,
        error_message: str
    ):
        """
        Update log ketika generasi gagal.

        Args:
            generation_id: ID dari generation log
            error_message: Pesan error yang terjadi
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE ai_generation_log
                SET generation_status = 'failed',
                    error_message = %s
                WHERE id = %s
            """, (error_message, generation_id))

            conn.commit()
            cursor.close()
            conn.close()

            logger.error(f"Generation error logged: ID {generation_id}, Error: {error_message}")

        except Exception as e:
            logger.error(f"Error updating generation error: {str(e)}")
            raise

    def get_generation_history(
        self,
        generation_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        generated_by: Optional[int] = None
    ) -> list:
        """
        Ambil history generasi dari database.

        Args:
            generation_type: Filter by generation type
            status: Filter by status ('pending', 'success', 'failed')
            limit: Batas jumlah record
            generated_by: Filter by user ID

        Returns:
            list: List of generation records
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            where_conditions = []
            params = []

            if generation_type:
                where_conditions.append("generation_type = %s")
                params.append(generation_type)

            if status:
                where_conditions.append("generation_status = %s")
                params.append(status)

            if generated_by:
                where_conditions.append("generated_by = %s")
                params.append(generated_by)

            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            query = f"""
                SELECT
                    id, assessment_task_id, generation_type, prompt_parameters,
                    source_materials, model_used, generation_status, error_message,
                    generated_by, created_at
                FROM ai_generation_log
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            # Parse JSON fields
            for result in results:
                if result['prompt_parameters']:
                    result['prompt_parameters'] = json.loads(result['prompt_parameters'])
                if result['source_materials']:
                    result['source_materials'] = json.loads(result['source_materials'])

            return results

        except Exception as e:
            logger.error(f"Error getting generation history: {str(e)}")
            return []

    def get_generation_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Ambil statistik generasi dalam N hari terakhir.

        Args:
            days: Jumlah hari untuk statistik

        Returns:
            Dict: Statistik generasi
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    generation_status,
                    model_used,
                    generation_type,
                    COUNT(*) as count
                FROM ai_generation_log
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY generation_status, model_used, generation_type
                ORDER BY count DESC
            """, (days,))

            stats = cursor.fetchall()

            cursor.close()
            conn.close()

            # Process statistics
            total_generations = sum(row['count'] for row in stats)
            successful_generations = sum(row['count'] for row in stats if row['generation_status'] == 'success')
            failed_generations = sum(row['count'] for row in stats if row['generation_status'] == 'failed')
            pending_generations = sum(row['count'] for row in stats if row['generation_status'] == 'pending')

            success_rate = (successful_generations / total_generations * 100) if total_generations > 0 else 0

            return {
                'period_days': days,
                'total_generations': total_generations,
                'successful_generations': successful_generations,
                'failed_generations': failed_generations,
                'pending_generations': pending_generations,
                'success_rate': round(success_rate, 2),
                'detailed_stats': stats
            }

        except Exception as e:
            logger.error(f"Error getting generation stats: {str(e)}")
            return {}

    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up logs lama untuk menjaga performa database.

        Args:
            days_to_keep: Jumlah hari logs yang akan disimpan
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM ai_generation_log
                WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days_to_keep,))

            deleted_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Cleaned up {deleted_rows} old generation logs (older than {days_to_keep} days)")

        except Exception as e:
            logger.error(f"Error cleaning up old logs: {str(e)}")


# Singleton instance untuk global access
generation_logger = AIGenerationLogger()