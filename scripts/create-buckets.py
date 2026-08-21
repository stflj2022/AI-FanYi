#!/usr/bin/env python3
"""
MinIO Bucket 初始化脚本
用于在 CI/CD 或开发环境中创建必要的 buckets
"""

import os
import sys
from minio import Minio
from minio.error import S3Error

def create_buckets():
    """创建 MinIO buckets"""

    # 从环境变量获取配置
    endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')
    secure = os.getenv('MINIO_USE_HTTPS', '0') == '1'

    # 需要创建的 buckets
    buckets = [
        'artifacts',
        'uploads',
        'models',
        'exports'
    ]

    try:
        # 初始化 MinIO 客户端
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )

        # 检查连接
        if not client.bucket_exists(buckets[0]):
            print(f"Connecting to MinIO at {endpoint}...")

        # 创建 buckets
        for bucket in buckets:
            try:
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
                    print(f"✓ Created bucket: {bucket}")

                    # 设置 bucket 策略（公共读）
                    policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"AWS": "*"},
                                "Action": ["s3:GetObject"],
                                "Resource": [f"arn:aws:s3:::{bucket}/*"]
                            }
                        ]
                    }
                    import json
                    client.set_bucket_policy(bucket, json.dumps(policy))
                else:
                    print(f"✓ Bucket already exists: {bucket}")
            except S3Error as e:
                print(f"✗ Error creating bucket {bucket}: {e}")
                return False

        print("\n✓ All MinIO buckets initialized successfully!")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == '__main__':
    success = create_buckets()
    sys.exit(0 if success else 1)
