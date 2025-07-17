from boto3.session import Session
from botocore.exceptions import BotoCoreError, ClientError

import datetime

aws_profile = "builder"
session = Session(profile_name=aws_profile)

dynamodb = session.resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table("RateLimitTable")


RATE_LIMIT = 2
TIME_WINDOW = 120


def is_rate_limited(ip: str):
    print(f"Checking rate limit for IP: {ip}", flush=True)

    response = table.get_item(Key={"ip_address": ip})
    item = response.get("Item")
    visits: list[str] = []

    if item:
        visits = item.get("visits", [])

    crr_time = datetime.datetime.now(datetime.timezone.utc)

    valid_visits = []

    for visit in visits:
        delta = crr_time - datetime.datetime.fromisoformat(visit)
        print(f"Visit: {visit}, Delta: {delta}", flush=True)
        if delta <= datetime.timedelta(seconds=TIME_WINDOW):
            valid_visits.append(visit)
        else:
            print(f"Removing visit: {visit} (out of time window)", flush=True)

    if len(valid_visits) >= RATE_LIMIT:
        return True

    valid_visits.append(crr_time.isoformat())

    table.put_item(Item={"ip_address": ip, "visits": valid_visits})

    return False


s3_base_url = "https://ascii-generator-123.s3.ap-south-1.amazonaws.com"


class S3Uploader:
    def __init__(self):
        self.bucket_name = "ascii-generator-123"
        self.s3 = session.client("s3", region_name="ap-south-1")

    def upload_file(self, content, s3_key, extra_args={}):
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                **extra_args,
            )
            print(f"Uploaded '{s3_key}' to bucket '{self.bucket_name}'")
        except (BotoCoreError, ClientError) as e:
            print(f"Upload failed: {e}")
