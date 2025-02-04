-- Copyright 2025 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--
-- SPDX-License-Identifier: Apache-2.0

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
