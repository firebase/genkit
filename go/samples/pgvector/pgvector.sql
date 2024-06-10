-- This SQL enables the vector extension and creates the table and data used
-- in the accompanying sample.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    show_id TEXT NOT NULL,
    season_number INTEGER NOT NULL,
    episode_id INTEGER NOT NULL,
    chunk TEXT,
    embedding vector(768),
    PRIMARY KEY (show_id, season_number, episode_id)
);

INSERT INTO embeddings (show_id, season_number, episode_id, chunk) VALUES 
	('La Vie', 1,  1,  'Natasha confesses her love for Pierre.'),
	('La Vie', 1,  2,  'Pierre and Natasha become engaged.'),
	('La Vie', 1,  3,  'Margot and Henri divorce.'),
	('Best Friends', 1,  1,  'Alice confesses her love for Oscar.'),
	('Best Friends', 1,  2,  'Oscar and Alice become engaged.'),
	('Best Friends', 1,  3,  'Bob and Pat divorce.')
;
