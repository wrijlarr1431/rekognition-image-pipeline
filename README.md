# rekognition-image-pipeline
# 🖼️ Rekognition Image Labeling Pipeline

Automated image analysis pipeline using Amazon Rekognition, DynamoDB, and GitHub Actions.

---

## 📋 Table of Contents

1. [AWS Resources Setup](#1-aws-resources-setup)
2. [GitHub Secrets Configuration](#2-github-secrets-configuration)
3. [Adding and Analyzing Images](#3-adding-and-analyzing-images)
4. [Verifying DynamoDB Logs](#4-verifying-dynamodb-logs)

---

## 1. AWS Resources Setup

### **Step 1: Create S3 Bucket**

```bash
# Create bucket for storing images
aws s3 mb s3://rekognition-images-js-2025 --region us-east-1

# Verify bucket was created
aws s3 ls | grep rekognition-images
```

### **Step 2: Create DynamoDB Tables**

```bash
# Beta Results Table: 
aws dynamodb create-table \
    --table-name beta_results \
    --attribute-definitions AttributeName=filename,AttributeType=S \
    --key-schema AttributeName=filename,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1  

# Production Results Table:
aws dynamodb create-table \
    --table-name prod_results \
    --attribute-definitions AttributeName=filename,AttributeType=S \
    --key-schema AttributeName=filename,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# Verify Tables: 
aws dynamodb list-tables --region us-east-1
```

### **Step 3: Create IAM User with Rekognition Access**

```bash
# Create User:
aws iam create-user --user-name rekognition-pipeline-user

# Attach Required Policies:

# S3 Full Access
aws iam attach-user-policy \
    --user-name rekognition-pipeline-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Rekognition Full Access
aws iam attach-user-policy \
    --user-name rekognition-pipeline-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonRekognitionFullAccess

# DynamoDB Full Access
aws iam attach-user-policy \
    --user-name rekognition-pipeline-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Create Access Keys: 
aws iam create-access-key --user-name rekognition-pipeline-user

# Output:
{
    "AccessKey": {
        "AccessKeyId": "AKIA...",
        "SecretAccessKey": "wJalr...",
        "Status": "Active"
    }
}
```

### **Step 4: Verify AWS Resources**

```bash 
Check results:

# Beta results
aws dynamodb scan --table-name beta_results --region us-east-1 --output json | jq '.Items'

# Production results
aws dynamodb scan --table-name prod_results --region us-east-1 --output json | jq '.Items'

# Expected Output:
{
  "filename": "rekognition-input/my-image.jpg",
  "branch": "main",
  "labels": "[{\"Name\": \"Person\", \"Confidence\": 99.5}]",
  "timestamp": "2025-12-02T19:21:28Z"
}

# Verify Data:

# Count items
aws dynamodb scan --table-name prod_results --region us-east-1 --select COUNT

# List S3 images
aws s3 ls s3://rekognition-images-js-2025/rekognition-input/
```

### Project Structure

rekognition-image-pipeline/
├── .github/workflows/
│   ├── on_pull_request.yml    # Beta workflow
│   └── on_merge.yml            # Production workflow
├── images/                     # Add images here
├── analyze_image.py
├── requirements.txt
└── README.md

### Quick Reference
```bash
# View production results
aws dynamodb scan --table-name prod_results --region us-east-1

# View beta results
aws dynamodb scan --table-name beta_results --region us-east-1

# List S3 images
aws s3 ls s3://rekognition-images-js-2025/rekognition-input/