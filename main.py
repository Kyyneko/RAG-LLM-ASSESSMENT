from flask import Flask, jsonify, render_template
from routes.rag_routes import rag_bp


def create_app() -> Flask:
    """
    Membuat instance Flask application dan melakukan konfigurasi awal.
    Termasuk pendaftaran blueprint serta pengaturan ukuran file maksimum.
    """
    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = "upload/"

    app.register_blueprint(rag_bp, url_prefix="/api/rag")
 
    @app.route("/")
    def home():
        """Landing page dengan tampilan yang cantik."""
        return render_template("index.html")
    
    @app.route("/api")
    def api_info():
        """Endpoint untuk memverifikasi status API (JSON response)."""
        return jsonify({
            "message": "SI-LAB RAG Assessment Generator API is running.",
            "version": "2.0",
            "status": "online",
            "endpoints": {
                "generate": "/api/rag/generate",
                "subjects": "/api/rag/subjects",
                "modules_by_subject": "/api/rag/subjects/<subject_id>/modules"
            }
        })

    @app.errorhandler(413)
    def too_large(e):
        """Menangani error jika file yang diunggah melebihi batas maksimum."""
        return jsonify({
            "error": "Ukuran file terlalu besar. Batas maksimum adalah 50MB."
        }), 413

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5002)