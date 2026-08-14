# Icelect Operation Guide

## Installation

First create a configuration file in `lib/config.py` based on `etc/config.py.example`.
In particular, you should the login credentials for the administrator and the
registrar.

Create a Python virtual environment, activate it and do `pip install -c constraints.txt .`.

An example systemd service file that runs the application using gunicorn
is in `etc/icelect.service.example`.

## Administration

Elections are mostly administered using the `icelect-admin` tool.
Invoke it with `--help` to see more details.

Some other actions are also available via the web interface (e.g.,
changing state of an election). Use the `/login` endpoint with the
admin's login credentials to gain privileges.

Each alection is in one of these states:

  - `init` - the election is vibisle only to the admin
  - `voting` - voting is open
  - `counting` - voting is closed, results are visible to admin and registrar
  - `results` - voting is closed, everybody sees the results

## Lifecycle of an election

1, create election configuratioon in `elections/$ELECTION.toml` (refer to `etc/election.toml.exmaple`).
2. create the election: `icelect-admin create $ELECTION` (it can be later updated
   using `icelect-admin update $ELECTION`).
3. the registrar uses `icelect-registrar cred -i $ELECTION -c $COUNT` to create credentials
3. receive `elections/$ELECTION.h2` from the registrar
4. set election state to `voting`
5. voters vote using their credentials
6. voters can check their ballots using their receipts and nonces
7. set election state to `counting`
8. the registrar downloads verifiers from the web interface, puts them to `elections/$ELECTION.verify` and runs `icelect-registrar verify --ident $ELECTION`;
   then they check the the number of unique verifiers reported matches the number of votes cast
9. compute the results by `icelect-admin results $ELECTION` and check them in the web interface
10. set election state to `results` to publish the results
