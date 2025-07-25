# IOI Committee Election

(c) 2025 Martin Mareš <mj@ucw.cz>

Placed under the MIT License.

## Protocol

Parties:

  - election server operator
  - registrar
  - voters

1. Generating credentials

  - The registrar generates _credentials_ (random strings of sufficient
    entropy), as many as there are voters.
  - For each credential, the registrar computes two independent cryptographic
    hases H1 and H2.
  - H2 hashes are given to the server operator.
  - H1 hashes are kept by the registrar.
  - The registrar hands out credentials to voters at random.
  - The registrar discards their copy of the (non-hashed) credentials.

2. Initializing election

  - The server operator sets up a new election with:
    - a random _election key_ KE
    - a random _verification key_ KV
    - the list of H2 hashes of credentials from the registrar
    - a list of options

3. Voting

  - Each voter sends the ballot to the server together with their credential
    and a nonce.
  - The server computes H1 and H2 of the credential and checks it that H2 is
    on the list of known H2 hashes.
  - The server computes a _receipt_: a keyed hash of H1 with the election key KE.
  - The server computes a _verifier_: a keyed hash of H1 with the verification key KV.
  - The server stores the sets of all verifiers and of all triples (receipt, nonce, ballot).
    If there is already a triple with the same receipt, it's overwritten (the voter
    changed their vote).
  - The receipt is sent to the voter.

4. Verification

  - After voting is closed, the list of (receipt, nonce, ballot) triples is published.
  - Voters (who know their receipts and nonces) can verify that their ballot was
    recorded properly.
  - Everybody in the room can check that the number of ballots does not exceed
    the number of voters present.
  - Optional: The server operator sends the list of verifiers and the verification
    key to the registrar, who can check that all verifiers correspond to valid H1
    hashes of credentials.

5. Evaluation

  - From the recorded ballots, we compute the results using the Schulze method.
  - Since the ballots are public, everybody can check that the results are
    correct.

### Security

Assuming that credentials are valid for a single election and that the server
operator does not collude with the registrar:

  - The server operator:
    - does not know which voter submitted which ballot (because credentials
      are distributed randomly, assuming there is no side channel that can
      tie network connections to voter identity
    - cannot change cast ballots, because voters can verify them using
      their receipts and nonces
    - cannot make up new ballots, because the number of ballots would not
      match the number of verifiers
    - cannot make up verifiers, because it would be discovered by the registrar
    - cannot add votes for absent/abstaining voters, because it has only
      the H2 hash of their credentials, but H1 is needed to produce a valid
      verifier (also, the case of impersonating absent voters would be
      detected by counting ballots)
    - Note that the credentials are never stored by the server, so any
      impersonation is possible only when the attacker can see the
      credentials being processed. So the server operator could do it,
      but somebody seeing the state of the server after the election is
      over cannot.

  - The registrar:
    - can impersonate any voter if the registrar keeps the unhashes credentials
        - impersonating a present voter is detected (review using receipts)
        - impersonating an absent voter is detected via ballot counting
        - impersonating an abstaining voter is possible
    - It's possible to make impersonation harder by having _two_ sets
      of credentials, each distributed by a different registrar, so both
      registrars would have to conspire. But I don't think it's worth
      the complications.

  - Other participants:
    - cannot tell which voter submitted which ballot
    - can see the whole list of ballots

Re-use of credentials for multiple elections:

  - The server operator could impersonate a voter who voted in one election,
    but abstained in another.
  - Observers cannot match votes cast by the same voter in different elections,
    because the receipts are keyed by the election key available only to the
    server operator.
  - The registrar also cannot match votes across elections: not by receipts
    (the registrar doesn't know the election key), nor by verifiers (the
    verifiers are not tied to particular ballots).
  - The registrar should check that the verification key wasn't recycled
    from a previous election.

Notable side-channels:

  - IP address: the GA hall will probably be behind a NAT, so the server will
    probably see all votes coming from the same IP address.
  - Cookies: the server must be placed in an unrelated domain to avoid leaking
    cookies from other sites in the same domain, which could leak information
    on voters' identity.
