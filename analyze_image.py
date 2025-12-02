import os
import sys
import json
from datetime import datetime
from pathlib import Path
import boto3

def validate_environment():
    """Validate all required environment variables exist"""
    required_vars = ['S3_BUCKET', 'AWS_REGION', 'DYNAMODB_TABLE', 'BRANCH_NAME']
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    print("✓ Environment validated")
    return {
        'bucket': os.environ['S3_BUCKET'],
        'region': os.environ['AWS_REGION'],
        'dynamodb_table': os.environ['DYNAMODB_TABLE'],
        'branch_name': os.environ['BRANCH_NAME']
    }

def get_image_files():
    """Get all image files from images/ folder"""
    images_dir = Path('images')
    
    if not images_dir.exists():
        print("❌ images/ folder not found")
        sys.exit(1)
    
    # Get all .jpg and .png files
    image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png'))
    
    if not image_files:
        print("⚠️  No image files found in images/")
        sys.exit(0)
    
    print(f"✓ Found {len(image_files)} image file(s)")
    return image_files

def upload_to_s3(s3_client, local_path, bucket, s3_key):
    """Upload a file to S3"""
    try:
        s3_client.upload_file(str(local_path), bucket, s3_key)
        print(f"✓ Uploaded to s3://{bucket}/{s3_key}")
        return f"s3://{bucket}/{s3_key}"
    except Exception as e:
        print(f"❌ Failed to upload {local_path}: {str(e)}")
        raise

def analyze_image_with_rekognition(rekognition_client, bucket, s3_key):
    """Analyze image using Amazon Rekognition"""
    print(f"🔍 Analyzing image with Rekognition...")
    
    try:
        response = rekognition_client.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': s3_key
                }
            },
            MaxLabels=10,
            MinConfidence=70
        )
        
        labels = response['Labels']
        print(f"✓ Detected {len(labels)} labels")
        
        # Format labels for storage
        formatted_labels = [
            {
                'Name': label['Name'],
                'Confidence': round(label['Confidence'], 2)
            }
            for label in labels
        ]
        
        return formatted_labels
        
    except Exception as e:
        print(f"❌ Rekognition analysis failed: {str(e)}")
        raise

def store_results_in_dynamodb(dynamodb_client, table_name, filename, labels, branch_name):
    """Store analysis results in DynamoDB"""
    print(f"💾 Storing results in DynamoDB table: {table_name}")
    
    try:
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        item = {
            'filename': filename,
            'timestamp': timestamp,
            'labels': labels,
            'branch': branch_name
        }
        
        dynamodb_client.put_item(
            TableName=table_name,
            Item={
                'filename': {'S': item['filename']},
                'timestamp': {'S': item['timestamp']},
                'labels': {'S': json.dumps(item['labels'])},
                'branch': {'S': item['branch']}
            }
        )
        
        print(f"✓ Results stored in DynamoDB")
        print(f"   Filename: {filename}")
        print(f"   Branch: {branch_name}")
        print(f"   Labels: {len(labels)} detected")
        
        return item
        
    except Exception as e:
        print(f"❌ Failed to store in DynamoDB: {str(e)}")
        raise

def process_single_image(image_file, config, s3_client, rekognition_client, dynamodb_client):
    """Process a single image through the entire pipeline"""
    print(f"\n{'='*60}")
    print(f"Processing: {image_file.name}")
    print(f"{'='*60}")
    
    bucket = config['bucket']
    dynamodb_table = config['dynamodb_table']
    branch_name = config['branch_name']
    
    # Step 1: Upload image to S3
    s3_key = f"rekognition-input/{image_file.name}"
    s3_uri = upload_to_s3(s3_client, image_file, bucket, s3_key)
    
    # Step 2: Analyze image with Rekognition
    labels = analyze_image_with_rekognition(rekognition_client, bucket, s3_key)
    
    # Step 3: Store results in DynamoDB
    result = store_results_in_dynamodb(
        dynamodb_client,
        dynamodb_table,
        s3_key,
        labels,
        branch_name
    )
    
    print(f"\n✅ Successfully processed {image_file.name}")
    print(f"   S3 Location: {s3_uri}")
    print(f"   DynamoDB Table: {dynamodb_table}")
    print(f"   Top Labels: {', '.join([l['Name'] for l in labels[:3]])}")

def main():
    """Main execution function"""
    print("🚀 Starting Rekognition Image Labeling Pipeline")
    print("="*60)
    
    # Validate environment
    config = validate_environment()
    
    # Get image files
    image_files = get_image_files()
    
    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name=config['region'])
    rekognition_client = boto3.client('rekognition', region_name=config['region'])
    dynamodb_client = boto3.client('dynamodb', region_name=config['region'])
    
    # Process each image file
    for image_file in image_files:
        try:
            process_single_image(
                image_file,
                config,
                s3_client,
                rekognition_client,
                dynamodb_client
            )
        except Exception as e:
            print(f"❌ Failed to process {image_file.name}: {str(e)}")
            continue
    
    print("\n" + "="*60)
    print("Pipeline completed!")
    print("="*60)

if __name__ == "__main__":
    main()