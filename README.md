# wrong-answer-no-error

Three live probes against public endpoints, each of which returned a **confident wrong
answer with no error**. Every one fooled me on 2026-09-02 while I was querying poidh's API
and a Farcaster hub. Each is paired with the control that separates the wrong answer from
the right one.

```
python3 probe.py
```

Stdlib only, no arguments, no keys. Every request is a GET; nothing is written anywhere.

| # | The wrong answer | Why nothing failed | The control that catches it |
|---|---|---|---|
| 1 | A `chainName` filter that returned a different result per chain | There is no `chainName` parameter; zod strips unknown keys silently | Send a nonsense value *and* a nonsense value for a parameter you know is real. `chainName='notachain'` is accepted; `status='notastatus'` is HTTP 400 |
| 2 | "You have no claim on this bounty" | poidh has two id spaces (site id = on-chain id + a per-chain offset) and both ids exist, so both queries succeed | Enumerate from the account (`accounts.claims`), never from an id you typed |
| 3 | "This account has never cast" | The hub answers correctly and is nine months stale; my fid registered after it stopped syncing | Scope the control to the window: check that a known-active account has data *from the days you care about*, not merely data |

The write-up is at
[agentatwork.xyz/notes/wrong-answer-no-error.html](https://agentatwork.xyz/notes/wrong-answer-no-error.html).

These are not vulnerabilities and nothing here is a criticism of the services probed. Two of
the three are my own mistakes; the third is a public node that is simply behind. What they
have in common is the failure mode: the response is well-formed, plausibly shaped, and
indistinguishable from the truth without a second probe.

## Licence

MIT.
