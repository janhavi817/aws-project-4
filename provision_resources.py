import boto3
import json
import time
from base64 import b64encode
import random
import string

def generate_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

def provision():
    iam = boto3.client('iam')
    s3 = boto3.client('s3', region_name='ap-south-1')
    ec2 = boto3.client('ec2', region_name='ap-south-1')
    ssm = boto3.client('ssm', region_name='ap-south-1')

    # Generating unique IDs for resources so you can run this script multiple times safely
    uid = generate_id()
    bucket_name = f"my-automated-bucket-{uid}"
    role_name = f"EC2-S3-ReadOnly-Role-{uid}"
    profile_name = f"EC2-S3-Profile-{uid}"
    sg_name = f"Web-SG-{uid}"

    print("Starting Automated Provisioning Script...")

    # 1. IAM Role & Instance Profile
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }
    
    print("[INFO] Creating IAM Role and Instance Profile...")
    iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy))
    iam.attach_role_policy(RoleName=role_name, PolicyArn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess')
    iam.create_instance_profile(InstanceProfileName=profile_name)
    iam.add_role_to_instance_profile(InstanceProfileName=profile_name, RoleName=role_name)
    print(f"[OK] IAM Role '{role_name}' created.")

    # We must wait a few seconds because IAM propagation takes time. If we launch the EC2 immediately, it might fail.
    print("[INFO] Waiting 10 seconds for IAM Profile to propagate globally...")
    time.sleep(10)

    # 2. S3 Bucket
    print(f"[INFO] Creating Private S3 Bucket '{bucket_name}'...")
    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'})
    
    # Uploading a file to the S3 bucket
    html_content = "<h1>Automated Provisioning Success!</h1><p>This HTML file was securely downloaded from a private S3 bucket by an EC2 instance using an IAM Role. No manual clicks required!</p>"
    s3.put_object(Bucket=bucket_name, Key='index.html', Body=html_content)
    print("[OK] S3 Bucket created and 'index.html' uploaded securely.")

    # 3. Security Group
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    
    sg = ec2.create_security_group(GroupName=sg_name, Description='Allow HTTP', VpcId=vpc_id)
    sg_id = sg['GroupId']
    ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}])
    print("[OK] Web Security Group created.")

    # 4. Launch EC2 Instance
    response = ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2')
    ami_id = response['Parameter']['Value']

    # The EC2 instance will use the AWS CLI to download the file from S3! 
    # Because we attach the IAM Instance Profile, we don't need any access keys!
    user_data = f"""#!/bin/bash
yum install -y httpd
systemctl start httpd
systemctl enable httpd
aws s3 cp s3://{bucket_name}/index.html /var/www/html/index.html
"""
    print("[INFO] Launching EC2 Instance...")
    instances = ec2.run_instances(
        ImageId=ami_id,
        InstanceType='t3.micro',
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': profile_name},
        UserData=b64encode(user_data.encode()).decode(),
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': f'Automated-EC2-{uid}'}]}]
    )
    
    instance_id = instances['Instances'][0]['InstanceId']
    print(f"[OK] EC2 Instance {instance_id} launched successfully.")
    
    print("[INFO] Waiting for instance to boot and receive a Public IP...")
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    
    inst_info = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = inst_info['Reservations'][0]['Instances'][0].get('PublicIpAddress', 'Unknown IP')

    print("\n============================================================")
    print("Provisioning Complete!")
    print(f"S3 Bucket: {bucket_name}")
    print(f"IAM Role: {role_name}")
    print(f"EC2 Public IP: {public_ip}")
    print(f"\nAccess your automated server: http://{public_ip}")
    print("Note: Give it 1-2 minutes for Apache to install and download the S3 file.")
    print("============================================================")

if __name__ == "__main__":
    provision()
