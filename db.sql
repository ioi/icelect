CREATE TYPE election_state AS ENUM (
	'init',		-- invisible to voters
	'voting',	-- voting is open
	'counting',	-- voting is closed, results visible only to admin
	'results'	-- voting is closed, results visible to everybody
);

CREATE TABLE elections (
	election_id	serial		PRIMARY KEY,
	ident		text		UNIQUE NOT NULL,
	state		election_state	NOT NULL DEFAULT 'init',
	config		jsonb		NOT NULL,
	election_key	text		NOT NULL,
	verify_key	text		NOT NULL,
	"order"		int		NOT NULL DEFAULT 0
);

-- H2 hashes of valid credentials
CREATE TABLE cred_hashes (
	election_id	int		NOT NULL REFERENCES elections(election_id),
	hash		text		NOT NULL,
	UNIQUE (election_id, hash)
);

CREATE TABLE ballots (
	election_id	int		NOT NULL REFERENCES elections(election_id),
	receipt		text		NOT NULL,
	nonce		text		NOT NULL,
	-- ranks of individual options (only order matters)
	ranks		smallint[]	NOT NULL,
	UNIQUE (election_id, receipt)
);

CREATE TABLE verifiers (
	election_id	int		NOT NULL REFERENCES elections(election_id),
	verifier	text		NOT NULL,
	UNIQUE (election_id, verifier)
);
