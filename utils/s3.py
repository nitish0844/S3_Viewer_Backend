import boto3


def get_s3_client(
    access_key,
    secret_key,
    region
):

    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )