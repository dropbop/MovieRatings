import os
import logging
import traceback
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file (when running locally)
load_dotenv()

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for movie ratings
INITIAL_ELO_VALUES = {
    'thumbs_down': 2000,
    'okay': 3000,
    'thumbs_up': 4000
}

def get_db_connection():
    """Create a connection to the database."""
    try:
        # Get the DATABASE_URL from environment variables
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return None
            
        # Connect to the database
        logger.info("Connecting to database")
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        return conn
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Database connection error: {e}\n{error_details}")
        return None

def init_movie_tables():
    """Initialize the movie ratings table."""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cursor:
            # Create the movie_ratings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movie_ratings (
                    id SERIAL PRIMARY KEY,
                    user_name VARCHAR(50) NOT NULL,
                    movie_title VARCHAR(255) NOT NULL,
                    elo_rating INTEGER NOT NULL DEFAULT 2500,
                    initial_rating VARCHAR(20) NOT NULL CHECK (initial_rating IN ('thumbs_down', 'okay', 'thumbs_up')),
                    rank_position INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_name, movie_title)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_movie_ratings_user 
                ON movie_ratings(user_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_movie_ratings_elo 
                ON movie_ratings(user_name, elo_rating DESC)
            """)
            
            logger.info("Movie ratings table initialized successfully")
            return True
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error initializing movie tables: {e}\n{error_details}")
        return False
    finally:
        conn.close()

def add_movie(user_name, movie_title, initial_rating):
    """Add a new movie with initial rating."""
    if initial_rating not in INITIAL_ELO_VALUES:
        logger.error(f"Invalid initial_rating: {initial_rating}")
        return None
        
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get initial ELO based on rating
            initial_elo = INITIAL_ELO_VALUES[initial_rating]
            
            # Insert the movie
            cursor.execute("""
                INSERT INTO movie_ratings (user_name, movie_title, elo_rating, initial_rating)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_name, movie_title, elo_rating, initial_rating, created_at
            """, (user_name, movie_title, initial_elo, initial_rating))
            
            movie = dict(cursor.fetchone())
            
            # Update rank positions for this user
            update_rank_positions(user_name)
            
            logger.info(f"Added movie: {movie_title} for user: {user_name}")
            return movie
            
    except psycopg2.IntegrityError:
        logger.error(f"Movie already exists: {movie_title} for user: {user_name}")
        return None
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error adding movie: {e}\n{error_details}")
        return None
    finally:
        conn.close()

def get_user_movies(user_name, category=None):
    """Get all movies for a user, optionally filtered by category."""
    conn = get_db_connection()
    if not conn:
        return []
        
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            if category:
                cursor.execute("""
                    SELECT id, user_name, movie_title, elo_rating, initial_rating, 
                           rank_position, created_at, updated_at
                    FROM movie_ratings
                    WHERE user_name = %s AND initial_rating = %s
                    ORDER BY elo_rating DESC
                """, (user_name, category))
            else:
                cursor.execute("""
                    SELECT id, user_name, movie_title, elo_rating, initial_rating, 
                           rank_position, created_at, updated_at
                    FROM movie_ratings
                    WHERE user_name = %s
                    ORDER BY elo_rating DESC
                """, (user_name,))
            
            movies = [dict(row) for row in cursor.fetchall()]
            return movies
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error getting user movies: {e}\n{error_details}")
        return []
    finally:
        conn.close()

def update_movie_elo(movie_id, new_elo):
    """Update a movie's ELO rating."""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cursor:
            # Update the ELO rating
            cursor.execute("""
                UPDATE movie_ratings
                SET elo_rating = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (new_elo, movie_id))
            
            # Get the user_name to update ranks
            cursor.execute("SELECT user_name FROM movie_ratings WHERE id = %s", (movie_id,))
            result = cursor.fetchone()
            
            if result:
                update_rank_positions(result[0])
                
            logger.info(f"Updated movie {movie_id} ELO to {new_elo}")
            return True
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error updating movie ELO: {e}\n{error_details}")
        return False
    finally:
        conn.close()

def update_rank_positions(user_name):
    """Update rank positions for all movies of a user based on ELO."""
    conn = get_db_connection()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                WITH ranked AS (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY elo_rating DESC) as new_rank
                    FROM movie_ratings
                    WHERE user_name = %s
                )
                UPDATE movie_ratings
                SET rank_position = ranked.new_rank
                FROM ranked
                WHERE movie_ratings.id = ranked.id
            """, (user_name,))
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error updating rank positions: {e}\n{error_details}")
    finally:
        conn.close()

def delete_movie(movie_id):
    """Delete a movie."""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cursor:
            # Get user_name before deletion
            cursor.execute("SELECT user_name FROM movie_ratings WHERE id = %s", (movie_id,))
            result = cursor.fetchone()
            
            if result:
                user_name = result[0]
                
                # Delete the movie
                cursor.execute("DELETE FROM movie_ratings WHERE id = %s", (movie_id,))
                
                # Update rank positions
                update_rank_positions(user_name)
                
                logger.info(f"Deleted movie {movie_id}")
                return True
            
            return False
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error deleting movie: {e}\n{error_details}")
        return False
    finally:
        conn.close()

# Keep the old camping functions below if you want to maintain both apps in the same DB
# Original camping calendar functions...
def get_preferences():
    """Fetch all preferences from the database."""
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to get database connection")
        return []
        
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
                SELECT user_name, event_date, preference_type 
                FROM preferences 
                ORDER BY event_date, user_name
            """)
            results = [dict(row) for row in cursor.fetchall()]
            
            # Convert date objects to strings for JSON serialization
            for row in results:
                row['event_date'] = row['event_date'].strftime('%Y-%m-%d')
                
            logger.info(f"Successfully retrieved {len(results)} preferences")
            return results
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error fetching preferences: {e}\n{error_details}")
        return []
    finally:
        conn.close()