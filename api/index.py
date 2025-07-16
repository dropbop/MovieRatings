import os
from flask import Flask, render_template, request, jsonify
import logging
import traceback
from .db import (
    get_db_connection, 
    init_movie_tables, 
    add_movie, 
    get_user_movies, 
    update_movie_elo, 
    delete_movie
)

# Configure more detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    """Renders the main movie ratings page."""
    try:
        return render_template('index.html')
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error rendering index page: {e}\n{error_details}")
        return "An error occurred loading the page. Please check server logs.", 500

@app.route('/api/movies', methods=['GET'])
def get_movies():
    """Get movies for a user, optionally filtered by category."""
    try:
        user_name = request.args.get('user', 'Jack')
        category = request.args.get('category')
        
        movies = get_user_movies(user_name, category)
        return jsonify(movies)
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error getting movies: {e}\n{error_details}")
        return jsonify({"error": "Failed to fetch movies"}), 500

@app.route('/api/movies', methods=['POST'])
def create_movie():
    """Add a new movie."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Invalid request body"}), 400
            
        user_name = data.get('user_name')
        movie_title = data.get('movie_title')
        initial_rating = data.get('initial_rating')
        
        # Validation
        if not user_name or not movie_title or not initial_rating:
            return jsonify({"error": "Missing required fields"}), 400
            
        if initial_rating not in ['thumbs_down', 'okay', 'thumbs_up']:
            return jsonify({"error": "Invalid initial_rating"}), 400
            
        # Add movie
        movie = add_movie(user_name, movie_title, initial_rating)
        
        if movie:
            return jsonify({"status": "success", "movie": movie}), 201
        else:
            return jsonify({"error": "Movie already exists or could not be added"}), 400
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error creating movie: {e}\n{error_details}")
        return jsonify({"error": "Failed to create movie"}), 500

@app.route('/api/movies/<int:movie_id>', methods=['PUT'])
def update_movie(movie_id):
    """Update a movie's ELO rating."""
    try:
        data = request.get_json()
        
        if not data or 'elo_rating' not in data:
            return jsonify({"error": "Missing elo_rating"}), 400
            
        elo_rating = data['elo_rating']
        
        # Validate ELO range
        if not isinstance(elo_rating, (int, float)) or elo_rating < 0 or elo_rating > 5000:
            return jsonify({"error": "Invalid elo_rating (must be 0-5000)"}), 400
            
        success = update_movie_elo(movie_id, int(elo_rating))
        
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Failed to update movie"}), 400
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error updating movie: {e}\n{error_details}")
        return jsonify({"error": "Failed to update movie"}), 500

@app.route('/api/movies/<int:movie_id>', methods=['DELETE'])
def delete_movie_endpoint(movie_id):
    """Delete a movie."""
    try:
        success = delete_movie(movie_id)
        
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Movie not found"}), 404
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error deleting movie: {e}\n{error_details}")
        return jsonify({"error": "Failed to delete movie"}), 500

@app.route('/init-movie-database')
def init_database():
    """Initialize the movie ratings database tables."""
    try:
        success = init_movie_tables()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Movie ratings table initialized successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to initialize movie tables"
            }), 500
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Database initialization failed: {e}\n{error_details}")
        return jsonify({
            "status": "error",
            "message": "Database initialization failed",
            "error": str(e)
        }), 500

@app.route('/database-status')
def database_status():
    """Check database connectivity and movie table status."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Connection failed"}), 500
        
    try:
        with conn.cursor() as cursor:
            # Check if movie_ratings table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'movie_ratings'
                )
            """)
            movie_table_exists = cursor.fetchone()[0]
            
            movie_count = 0
            if movie_table_exists:
                cursor.execute("SELECT COUNT(*) FROM movie_ratings")
                movie_count = cursor.fetchone()[0]
            
            return jsonify({
                "status": "connected",
                "movie_table_exists": movie_table_exists,
                "movie_count": movie_count,
                "message": "Database connection successful"
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Database error: {str(e)}"
        }), 500
    finally:
        conn.close()

# This is needed if running locally with `python api/index.py`
if __name__ == '__main__':
    # Make sure debug=False for production environments
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    logger.info(f"Starting Flask app in {'debug' if debug_mode else 'production'} mode")
    app.run(debug=debug_mode, port=5000)