"""The live broadcast's upload to an Amazon S3 bucket (--broadcast CHANNEL --bucket NAME; live_broadcast.Broadcaster
takes it as its target). Its own module so the packaged helper can leave it out (build_helper.bat excludes it): the
public exe has no way to send anything off the computer, and only the user's own launcher (Python, with the AWS
profile and bucket set) broadcasts."""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from systems.common import ROOT  # noqa: E402


class S3Target:
    """Uploads with boto3, or with the AWS command line when boto3 has no credentials it can use. Both take the
    credentials of the AWS_PROFILE named in the environment (the live launcher sets it), so a user that may only
    write under live/ in the bucket is enough."""

    def __init__(self, bucket, prefix):
        self.bucket, self.prefix = bucket, prefix.strip("/")
        self.client = None
        try:
            import boto3
            boto3.client("sts").get_caller_identity()  # credentials that work (needs no permission)
            self.client = boto3.client("s3")
        except Exception:
            self.client = None
        self.url = f"https://{bucket}.s3.amazonaws.com/{self.prefix}/index.html"

    def put(self, key, body, content_type, encoding=None, cache="no-cache, max-age=0"):
        key = f"{self.prefix}/{key}"
        if self.client:
            extra = {"ContentType": content_type, "CacheControl": cache}
            if encoding:
                extra["ContentEncoding"] = encoding
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body, **extra)
            return
        tmp = ROOT / "captures" / "_live_upload.tmp"
        tmp.write_bytes(body)
        cmd = ["aws", "s3", "cp", str(tmp), f"s3://{self.bucket}/{key}", "--content-type", content_type,
               "--cache-control", cache, "--only-show-errors"]
        if encoding:
            cmd += ["--content-encoding", encoding]
        cmd[0] = shutil.which("aws") or "aws"
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip()[-300:])
