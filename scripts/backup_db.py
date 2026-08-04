import gzip
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config


def backup_db():
    db_path = config.DATABASE
    if not os.path.exists(db_path):
        print(f'DB not found: {db_path}')
        return False

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    backup_name = f'archestate_{timestamp}.db.gz'
    backup_path = os.path.join(backup_dir, backup_name)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db')
    os.close(tmp_fd)

    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(tmp_path)
        src.backup(dst)
        src.close()
        dst.close()

        with open(tmp_path, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        print(f'Backup created: {backup_path} ({size_mb:.2f} MB)')

        backup_s3_bucket = os.environ.get('BACKUP_S3_BUCKET', '')
        if backup_s3_bucket:
            _upload_to_s3(backup_path, backup_name, backup_s3_bucket)

        _cleanup_old_backups(backup_dir, keep=7)

        return True
    except Exception:
        print(f'Error creating backup', exc_info=True)
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _upload_to_s3(local_path, filename, bucket):
    try:
        import boto3
        access_key = os.environ.get('BACKUP_S3_ACCESS_KEY', '')
        secret_key = os.environ.get('BACKUP_S3_SECRET_KEY', '')
        region = os.environ.get('BACKUP_S3_REGION', 'us-east-1')

        if access_key and secret_key:
            s3 = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
        else:
            s3 = boto3.client('s3', region_name=region)

        s3.upload_file(local_path, bucket, f'db-backups/{filename}')
        print(f'Uploaded to s3://{bucket}/db-backups/{filename}')
    except ImportError:
        print('boto3 not installed. Skipping S3 upload.')
    except Exception:
        print(f'Error uploading to S3', exc_info=True)


def _cleanup_old_backups(backup_dir, keep=7):
    try:
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith('archestate_') and f.endswith('.db.gz')],
            reverse=True
        )
        for old in backups[keep:]:
            os.remove(os.path.join(backup_dir, old))
            print(f'Removed old backup: {old}')
    except Exception:
        print(f'Error cleaning old backups', exc_info=True)


if __name__ == '__main__':
    start = time.time()
    success = backup_db()
    elapsed = time.time() - start
    print(f'Backup {"OK" if success else "FAILED"} ({elapsed:.2f}s)')
    sys.exit(0 if success else 1)
