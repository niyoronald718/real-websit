INSERT OR IGNORE INTO vjs (id, name, slug, bio) VALUES
(1, 'Nabirye Kato', 'nabirye-kato', 'Luganda Vj and storyteller.'),
(2, 'Musa Ssemanda', 'musa-ssemanda', 'Vj focused on drama and adventure.'),
(3, 'Sarah Nansubuga', 'sarah-nansubuga', 'Luganda narrator and performer.'),
(4, 'Kato Lwanga', 'kato-lwanga', 'Independent Vj.'),
(5, 'Amina Nakato', 'amina-nakato', 'Performer and translator.'),
(6, 'Peter Ssekandi', 'peter-ssekandi', 'Vj and director.');

INSERT OR IGNORE INTO genres (id, name, slug) VALUES
(1, 'Drama', 'drama'), (2, 'Comedy', 'comedy'), (3, 'Action', 'action'),
(4, 'Adventure', 'adventure'), (5, 'Family', 'family'), (6, 'Mystery', 'mystery'),
(7, 'Romance', 'romance'), (8, 'Documentary', 'documentary');

INSERT OR IGNORE INTO movies
(id, title, slug, description, year, duration, rating, type, is_new, is_hot, is_featured, is_published, is_downloadable, vj_id)
VALUES
(1, 'The River Promise', 'the-river-promise', 'A fictional story about a family rebuilding their lives beside a changing river.', 2025, 108, 7.4, 'movie', 1, 1, 1, 1, 1, 1),
(2, 'Market Day', 'market-day', 'Two friends turn an ordinary market day into an unforgettable adventure.', 2024, 96, 7.1, 'movie', 1, 0, 1, 1, 1, 2),
(3, 'The Last Letter', 'the-last-letter', 'A mystery begins when an old letter arrives years after it was sent.', 2023, 114, 8.0, 'movie', 0, 1, 0, 1, 1, 3),
(4, 'Hilltop Neighbors', 'hilltop-neighbors', 'A warm comedy about neighbors learning to work together.', 2024, 89, 6.9, 'movie', 1, 0, 0, 1, 1, 4),
(5, 'A New Morning', 'a-new-morning', 'A young artist finds courage to begin again in a new town.', 2022, 102, 7.6, 'movie', 0, 0, 0, 1, 1, 5),
(6, 'The Green Path', 'the-green-path', 'A group of friends follows a map through the countryside.', 2025, 99, 7.2, 'movie', 1, 1, 0, 1, 1, 6),
(7, 'Small Victories', 'small-victories', 'A family discovers that everyday kindness can change a community.', 2021, 93, 7.8, 'movie', 0, 0, 0, 1, 1, 1),
(8, 'Across the Valley', 'across-the-valley', 'A fictional adventure of friendship, trust, and a long journey.', 2023, 121, 7.5, 'movie', 0, 1, 0, 1, 1, 2),
(9, 'The Quiet House', 'the-quiet-house', 'A quiet house holds a puzzle that brings three generations together.', 2022, 105, 7.0, 'movie', 0, 0, 0, 1, 1, 3),
(10, 'Second Chances', 'second-chances', 'An uplifting romance about unexpected beginnings.', 2024, 98, 7.3, 'movie', 1, 0, 0, 1, 1, 4),
(11, 'Our Shared Garden', 'our-shared-garden', 'A neighborhood project grows into something bigger than anyone expected.', 2025, 87, 6.8, 'movie', 1, 0, 0, 1, 1, 5),
(12, 'Stories from Home', 'stories-from-home', 'A fictional anthology celebrating community and home.', 2023, 110, 7.7, 'movie', 0, 0, 0, 1, 1, 6);

INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES
(1,1),(1,5),(2,2),(2,4),(3,1),(3,6),(4,2),(4,5),(5,1),(5,7),
(6,3),(6,4),(7,1),(7,5),(8,3),(8,4),(9,1),(9,6),(10,2),(10,7),
(11,5),(11,8),(12,1),(12,8);
