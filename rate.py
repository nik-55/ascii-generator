import datetime

visitors = {}

RATE_LIMIT = 2
TIME_WINDOW = 120

def is_rate_limited(ip: str):
    print(f"Checking rate limit for IP: {ip}", flush=True)
    print(f"Current visitors: {visitors}", flush=True)
    visits = visitors.get(ip, [])

    crr_time = datetime.datetime.now()

    valid_visits = []

    for visit in visits:
        delta = crr_time - visit
        print(f"Visit: {visit}, Delta: {delta}", flush=True)
        if delta <= datetime.timedelta(seconds=TIME_WINDOW):
            valid_visits.append(visit)
        else:
            print(f"Removing visit: {visit} (out of time window)", flush=True)

    if len(valid_visits) >= RATE_LIMIT:
        return True

    valid_visits.append(crr_time)

    visitors[ip] = valid_visits

    return False
