from . import config
from pathlib import Path

BASE_PATH = Path(config.FILE_BASE_PATH)
if not BASE_PATH.is_absolute():
    BASE_PATH = BASE_PATH.absolute()


def get_file_path(pool: str, id: int | str) -> Path:
    """
    Takes a pool and file ID and returns the path (with subdirectory prefix) where the file should be stored.
    """
    if isinstance(id, str) and len(id) == 44:
        prefix = id[0:2]
    else:
        if not isinstance(id, int):
            id = int(id)
        prefix = "{:03d}".format(id % 1000)

    return BASE_PATH / pool / prefix / f"{id}"


_r2 = None


def _bucket():
    """CubeOS: the S3 client for the configured R2 bucket, or None to use local disk."""
    global _r2
    if not getattr(config, "R2_BUCKET", None):
        return None
    if _r2 is None:
        import boto3
        from botocore.config import Config

        _r2 = boto3.client(
            "s3",
            endpoint_url=config.R2_ENDPOINT,
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(retries={"max_attempts": 4, "mode": "standard"}),
        )
    return _r2


def _key(pool: str, id: int | str) -> str:
    return str(get_file_path(pool, id).relative_to(BASE_PATH))


def store(pool: str, id: int | str, body: bytes):
    """
    Stores a file into the configured storage directory, creating the directory prefix (if needed).
    CubeOS: or into the R2 bucket, when one is configured.
    """

    r2 = _bucket()
    if r2 is not None:
        r2.put_object(Bucket=config.R2_BUCKET, Key=_key(pool, id), Body=body)
        return

    store = get_file_path(pool, id)
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_bytes(body)


def read(pool: str, id: int | str) -> bytes:
    """CubeOS: a stored file's contents, from the R2 bucket or local disk."""
    r2 = _bucket()
    if r2 is not None:
        return r2.get_object(Bucket=config.R2_BUCKET, Key=_key(pool, id))["Body"].read()
    return get_file_path(pool, id).read_bytes()


def size(pool: str, id: int | str) -> int:
    """CubeOS: a stored file's size in bytes, from the R2 bucket or local disk."""
    r2 = _bucket()
    if r2 is not None:
        return int(r2.head_object(Bucket=config.R2_BUCKET, Key=_key(pool, id))["ContentLength"])
    return get_file_path(pool, id).stat().st_size


def delete(pool: str, id: int | str):
    """CubeOS: removes a stored file (missing is fine), from the R2 bucket or local disk."""
    r2 = _bucket()
    if r2 is not None:
        r2.delete_object(Bucket=config.R2_BUCKET, Key=_key(pool, id))
        return
    get_file_path(pool, id).unlink(missing_ok=True)
