#!/usr/bin/env python3
"""Three live probes, each of which returned a confident wrong answer with no error.

Every one of these fooled me on 2026-09-02 while querying poidh's API and a Farcaster hub.
None returned an error, a warning, or an empty result. Each is paired here with the control
that separates the wrong answer from the right one.

    python3 probe.py

Stdlib only. Read-only: every request is a GET.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "wrong-answer-no-error/1.0 (+https://github.com/agentatwork/wrong-answer-no-error)"
TRPC = "https://poidh.xyz/api/trpc/%s?input=%s"
CHAIN = {1: "mainnet", 8453: "base", 42161: "arbitrum", 666666666: "degen"}


def trpc(path, inp, timeout=35):
    """Returns (payload, None) or (None, 'HTTP nnn')."""
    url = TRPC % (path, urllib.parse.quote(json.dumps({"json": inp})))
    req = urllib.request.Request(url, headers={"user-agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as f:
            return json.load(f)["result"]["data"]["json"], None
    except urllib.error.HTTPError as e:
        return None, "HTTP %d" % e.code


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"user-agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def fingerprint(items):
    """What the caller actually consumes: which chains, and which rows."""
    chains = {}
    for b in items:
        chains[CHAIN.get(b["chainId"], b["chainId"])] = chains.get(
            CHAIN.get(b["chainId"], b["chainId"]), 0) + 1
    return len(items), chains, [b["id"] for b in items[:5]]


def probe_invented_parameter():
    print("1. A parameter that does not exist")
    print("   bounties.fetchAll, asked to filter by chain five different ways.\n")
    base = {"status": "open", "limit": 30, "sortType": "date"}
    cases = [("chainName='base'", {**base, "chainName": "base"}),
             ("chainName='degen'", {**base, "chainName": "degen"}),
             ("chainName='notachain'", {**base, "chainName": "notachain"}),
             ("chainName=''", {**base, "chainName": ""}),
             ("chainName absent", dict(base)),
             ("chainId=8453", {**base, "chainId": 8453})]
    seen = set()
    for label, inp in cases:
        d, err = trpc("bounties.fetchAll", inp)
        if err:
            print("   %-24s -> %s" % (label, err)); continue
        n, chains, ids = fingerprint(d["items"])
        seen.add(json.dumps([n, chains, ids], sort_keys=True))
        print("   %-24s -> %2d rows %s" % (label, n, chains))
    print("\n   distinct answers: %d" % len(seen))
    # The control. If the endpoint validated nothing at all, the six identical answers
    # above would prove nothing -- so ask it something it *does* validate.
    _, err = trpc("bounties.fetchAll", {**base, "status": "notastatus"})
    print("   control: status='notastatus' -> %s" % (err or "accepted (!)"))
    print("   => validation is live; `chainName` is simply not a parameter, and zod")
    print("      strips unknown keys silently. The filter I invented looked like it worked.\n")


def probe_two_namespaces():
    print("2. A real id in the wrong namespace")
    print("   poidh site ids are on-chain ids plus a per-chain offset (base: +986).")
    print("   Both calls below succeed. One is about a bounty I have never touched.\n")
    me = "0x1c7afa67130ee637765a8281e83342e307409d57"
    for label, bid in [("bountyId=348   (on-chain id)", 348),
                       ("bountyId=1334  (site id)", 1334)]:
        d, err = trpc("claims.fetchBountyClaims",
                      {"bountyId": bid, "chainId": 8453, "limit": 100})
        if err:
            print("   %-28s -> %s" % (label, err)); continue
        items = d.get("items", [])
        mine = [c["id"] for c in items if (c.get("issuer") or "").lower() == me]
        print("   %-28s -> %2d claims, %d mine %s"
              % (label, len(items), len(mine), mine))
    b, _ = trpc("bounties.fetch", {"id": 1334, "chainId": 8453})
    print("\n   site 1334 is: %r" % (b or {}).get("title"))
    print("   => no error distinguishes them. Reading the on-chain id told me, with")
    print("      total confidence, that I had no claim on my own largest claim.\n")


def probe_stale_node():
    print("3. A node that answers, and cannot see")
    print("   Same query, two Farcaster hubs.\n")
    hubs = [("hub.pinata.cloud", "https://hub.pinata.cloud"),
            ("snap.farcaster.xyz", "https://snap.farcaster.xyz:3381")]
    fids = [(3, "dwr, known active"), (3346381, "me"), (99999999, "does not exist")]
    for hname, h in hubs:
        print("   %s" % hname)
        for fid, label in fids:
            try:
                d = get("%s/v1/castsByFid?fid=%d&pageSize=5&reverse=true" % (h, fid))
                ms = d.get("messages", [])
                newest = ""
                if ms:
                    import datetime
                    ts = 1609459200 + ms[0]["data"]["timestamp"]
                    newest = datetime.datetime.utcfromtimestamp(ts).strftime(
                        "  newest %Y-%m-%d")
                print("     fid %-9d %-18s -> %d messages%s"
                      % (fid, label, len(ms), newest))
            except Exception as e:
                print("     fid %-9d %-18s -> %s" % (fid, label, type(e).__name__))
    print("\n   => the stale hub returns 0 for me, exactly as it does for a fid that was")
    print("      never registered. The positive control (dwr has casts) passes on both.")
    print("      Only the *date* of dwr's newest cast separates them.\n")


def main():
    print(__doc__.strip().splitlines()[0] + "\n")
    for fn in (probe_invented_parameter, probe_two_namespaces, probe_stale_node):
        try:
            fn()
        except Exception as e:
            print("   probe failed: %s: %s\n" % (type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
