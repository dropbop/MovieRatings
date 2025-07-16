document.addEventListener('DOMContentLoaded', () => {
    // State management
    let currentUser = 'Jack';
    let currentFilter = 'all';
    let comparisonQueue = [];
    let newMovie = null;
    
    // DOM elements
    const userButtons = document.getElementById('user-buttons');
    const addUserBtn = document.getElementById('add-user-btn');
    const movieTitleInput = document.getElementById('movie-title');
    const ratingButtons = document.querySelectorAll('.rating-btn');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const movieList = document.getElementById('movie-list');
    const messageArea = document.getElementById('message-area');
    const comparisonModal = document.getElementById('comparison-modal');
    const movieABtn = document.getElementById('movie-a');
    const movieBBtn = document.getElementById('movie-b');
    const equalBtn = document.getElementById('equal-btn');
    
    // Initialize
    loadUserMovies();
    
    // User selection
    userButtons.addEventListener('click', (e) => {
        if (e.target.classList.contains('user-button')) {
            userButtons.querySelectorAll('.user-button').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            currentUser = e.target.dataset.user;
            loadUserMovies();
        }
    });
    
    // Add new user
    addUserBtn.addEventListener('click', () => {
        const userName = prompt('Enter new user name:');
        if (userName && userName.trim()) {
            const newBtn = document.createElement('button');
            newBtn.type = 'button';
            newBtn.className = 'user-button';
            newBtn.dataset.user = userName.trim();
            newBtn.textContent = userName.trim();
            userButtons.insertBefore(newBtn, addUserBtn);
        }
    });
    
    // Rating buttons
    ratingButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const title = movieTitleInput.value.trim();
            if (!title) {
                showMessage('Please enter a movie title', 'error');
                return;
            }
            
            const rating = btn.dataset.rating;
            await addMovie(title, rating);
        });
    });
    
    // Filter buttons
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            loadUserMovies();
        });
    });
    
    // Comparison modal buttons
    movieABtn.addEventListener('click', () => handleComparison('a'));
    movieBBtn.addEventListener('click', () => handleComparison('b'));
    equalBtn.addEventListener('click', () => handleComparison('equal'));
    
    // Add movie function
    async function addMovie(title, initialRating) {
        try {
            showMessage('Adding movie...', 'info');
            
            // First, create the movie with initial rating
            const response = await fetch('/api/movies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_name: currentUser,
                    movie_title: title,
                    initial_rating: initialRating
                })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.message || 'Failed to add movie');
            }
            
            newMovie = result.movie;
            
            // Get movies in the same category for comparison
            const categoryMovies = await getMoviesInCategory(initialRating);
            
            if (categoryMovies.length > 0) {
                // Start binary comparison
                startBinaryComparison(categoryMovies);
            } else {
                // No movies to compare, we're done
                showMessage('Movie added successfully!', 'success');
                movieTitleInput.value = '';
                loadUserMovies();
            }
            
        } catch (error) {
            showMessage(error.message, 'error');
        }
    }
    
    // Get movies in a specific category
    async function getMoviesInCategory(category) {
        const response = await fetch(`/api/movies?user=${currentUser}&category=${category}`);
        const movies = await response.json();
        return movies.filter(m => m.id !== newMovie.id);
    }
    
    // Binary comparison algorithm
    function startBinaryComparison(movies) {
        // Sort movies by current ELO
        movies.sort((a, b) => b.elo_rating - a.elo_rating);
        
        // Initialize binary search
        let low = 0;
        let high = movies.length - 1;
        let mid = Math.floor((low + high) / 2);
        
        comparisonQueue = [{
            movies: movies,
            low: low,
            high: high,
            mid: mid,
            compareTo: movies[mid]
        }];
        
        showNextComparison();
    }
    
    function showNextComparison() {
        if (comparisonQueue.length === 0) {
            // Comparisons complete
            finishRanking();
            return;
        }
        
        const current = comparisonQueue[0];
        movieABtn.textContent = newMovie.movie_title;
        movieBBtn.textContent = current.compareTo.movie_title;
        comparisonModal.classList.remove('hidden');
    }
    
    async function handleComparison(choice) {
        const current = comparisonQueue.shift();
        let newElo = newMovie.elo_rating;
        
        if (choice === 'a') {
            // New movie is better
            newElo = current.compareTo.elo_rating + 50;
            current.low = current.mid + 1;
        } else if (choice === 'b') {
            // Existing movie is better
            newElo = current.compareTo.elo_rating - 50;
            current.high = current.mid - 1;
        } else {
            // Equal
            newElo = current.compareTo.elo_rating;
            current.low = current.high + 1; // End search
        }
        
        // Update the new movie's ELO
        newMovie.elo_rating = Math.max(0, Math.min(5000, newElo));
        
        if (current.low <= current.high) {
            // Continue binary search
            current.mid = Math.floor((current.low + current.high) / 2);
            current.compareTo = current.movies[current.mid];
            comparisonQueue.unshift(current);
        }
        
        showNextComparison();
    }
    
    async function finishRanking() {
        comparisonModal.classList.add('hidden');
        
        // Update movie with final ELO
        try {
            await fetch(`/api/movies/${newMovie.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    elo_rating: newMovie.elo_rating
                })
            });
            
            showMessage('Movie ranked successfully!', 'success');
            movieTitleInput.value = '';
            loadUserMovies();
        } catch (error) {
            showMessage('Failed to save ranking', 'error');
        }
    }
    
    // Load user movies
    async function loadUserMovies() {
        try {
            const response = await fetch(`/api/movies?user=${currentUser}`);
            const movies = await response.json();
            
            // Filter movies
            let filteredMovies = movies;
            if (currentFilter !== 'all') {
                filteredMovies = movies.filter(m => m.initial_rating === currentFilter);
            }
            
            // Sort by ELO descending
            filteredMovies.sort((a, b) => b.elo_rating - a.elo_rating);
            
            // Display movies
            displayMovies(filteredMovies);
            
        } catch (error) {
            showMessage('Failed to load movies', 'error');
        }
    }
    
    function displayMovies(movies) {
        movieList.innerHTML = '';
        
        movies.forEach((movie, index) => {
            const movieEl = document.createElement('div');
            movieEl.className = 'movie-item';
            movieEl.innerHTML = `
                <div class="movie-rank">#${index + 1}</div>
                <div class="movie-info">
                    <div class="movie-title">${movie.movie_title}</div>
                    <div class="movie-meta">
                        <span class="movie-stars">${getStarRating(movie.elo_rating)}</span>
                        <span class="movie-elo">ELO: ${movie.elo_rating}</span>
                        <span class="movie-category">${getCategoryEmoji(movie.initial_rating)}</span>
                    </div>
                </div>
                <button class="delete-btn" data-id="${movie.id}">×</button>
            `;
            
            movieEl.querySelector('.delete-btn').addEventListener('click', () => deleteMovie(movie.id));
            movieList.appendChild(movieEl);
        });
        
        if (movies.length === 0) {
            movieList.innerHTML = '<div class="no-movies">No movies yet. Add your first movie above!</div>';
        }
    }
    
    function getStarRating(elo) {
        // Convert ELO (0-5000) to stars (1.0-5.0)
        const stars = 1 + (elo / 5000) * 4;
        return '⭐ ' + stars.toFixed(1);
    }
    
    function getCategoryEmoji(category) {
        const emojis = {
            'thumbs_up': '👍',
            'okay': '👌',
            'thumbs_down': '👎'
        };
        return emojis[category] || '';
    }
    
    async function deleteMovie(movieId) {
        if (!confirm('Delete this movie?')) return;
        
        try {
            const response = await fetch(`/api/movies/${movieId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showMessage('Movie deleted', 'success');
                loadUserMovies();
            }
        } catch (error) {
            showMessage('Failed to delete movie', 'error');
        }
    }
    
    function showMessage(message, type = 'info') {
        messageArea.textContent = message;
        messageArea.className = `message-area ${type}`;
        
        if (type === 'success' || type === 'error') {
            setTimeout(() => {
                messageArea.textContent = '';
                messageArea.className = 'message-area';
            }, 3000);
        }
    }
});