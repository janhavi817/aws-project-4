# Automate AWS Resource Provisioning

This project perfectly demonstrates Infrastructure as Code (IaC) by completely removing manual clicks from the AWS Console. Everything is securely provisioned via Boto3.

## Services Automated
1. **AWS IAM**: Creates an IAM Role and Instance Profile dynamically with `AmazonS3ReadOnlyAccess`.
2. **Amazon S3**: Creates a completely private S3 bucket and uploads an `index.html` file to it.
3. **Amazon EC2**: Provisions a web server, attaches the secure IAM Instance Profile, and automatically executes a startup script.

## The Magic
When the EC2 instance boots up, it securely uses the attached IAM Role to run the command `aws s3 cp s3://my-bucket/index.html /var/www/html/index.html`. It pulls the web page code directly from the private S3 bucket without requiring any hardcoded AWS Access Keys or Secrets!

## Run the Automation
```powershell
python provision_resources.py
```
Wait a few minutes, then open the Public IP in your browser!
