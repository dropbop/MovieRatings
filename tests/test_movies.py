from tests.conftest import auth_headers


def test_create_movie_authorized(client):
    client.post('/register', json={'user_name': 'alice', 'password': 'pwd'})
    headers = auth_headers('alice', 'pwd')

    resp = client.post('/api/movies', json={
        'user_name': 'alice',
        'movie_title': 'Matrix',
        'initial_rating': 'thumbs_up'
    }, headers=headers)
    assert resp.status_code == 201
    movie = resp.get_json()['movie']
    assert movie['movie_title'] == 'Matrix'


def test_create_movie_unauthorized(client):
    resp = client.post('/api/movies', json={
        'user_name': 'someone',
        'movie_title': 'Hackers',
        'initial_rating': 'thumbs_up'
    })
    assert resp.status_code == 401


def test_movie_listing_and_update(client):
    client.post('/register', json={'user_name': 'bob', 'password': 'pwd'})
    headers = auth_headers('bob', 'pwd')

    r1 = client.post('/api/movies', json={'user_name': 'bob', 'movie_title': 'A', 'initial_rating': 'thumbs_up'}, headers=headers)
    r2 = client.post('/api/movies', json={'user_name': 'bob', 'movie_title': 'B', 'initial_rating': 'okay'}, headers=headers)
    id_a = r1.get_json()['movie']['id']
    id_b = r2.get_json()['movie']['id']

    # list with filter
    resp = client.get('/api/movies?user=bob&category=thumbs_up')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    # update elo
    resp = client.put(f'/api/movies/{id_a}', json={'elo_rating': 4100}, headers=headers)
    assert resp.status_code == 200

    # compare movies
    resp = client.post('/api/compare', json={'movie_a_id': id_a, 'movie_b_id': id_b, 'result': 'a'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['movie_a_id'] == id_a

    # delete movie
    resp = client.delete(f'/api/movies/{id_b}', headers=headers)
    assert resp.status_code == 200
