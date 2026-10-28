from datetime import timedelta


def is_active(vote, now, ttl_min):
    return vote is not None and (now - vote.ts) <= timedelta(minutes=ttl_min)


def store_vote(votes, name, vote, now, ttl_min):
    """الصوت المحايد الجديد ما يلغي صوتاً قوياً ما زال صالحاً."""
    if vote is None:
        return
    old = votes.get(name)
    if (vote.direction == "NEUTRAL" and is_active(old, now, ttl_min)
            and old.direction != "NEUTRAL"):
        return
    votes[name] = vote


def agree(votes, names, now, ttl_min, min_conf):
    """يرجع BUY أو SELL إذا كل الأسماء نفس الاتجاه وثقتهم كافية، وإلا None."""
    vs = [votes.get(n) for n in names]
    if not all(is_active(v, now, ttl_min) for v in vs):
        return None
    dirs = {v.direction for v in vs}
    if len(dirs) != 1:
        return None
    d = dirs.pop()
    if d not in ("BUY", "SELL"):
        return None
    if any(v.confidence < min_conf for v in vs):
        return None
    return d
