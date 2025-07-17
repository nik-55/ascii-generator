terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region  = "ap-south-1"
  profile = "builder"
}


resource "aws_s3_bucket" "ascii" {
  bucket        = "ascii-generator-123"
  force_destroy = true

  tags = {
    Mode = "builder"
  }
}

resource "aws_s3_bucket_public_access_block" "ascii-public-access-block" {
  bucket = aws_s3_bucket.ascii.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

data "aws_iam_policy_document" "allow_public_access" {
  statement {
    actions = ["s3:GetObject"]
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.ascii.id}/*"
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    effect = "Allow"
    sid    = "allow-public-access"
  }
}

resource "aws_s3_bucket_policy" "allow_public_access" {
  bucket = aws_s3_bucket.ascii.id
  policy = data.aws_iam_policy_document.allow_public_access.json
}

resource "aws_dynamodb_table" "rate-limit-table" {
  name         = "RateLimitTable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ip_address"

  attribute {
    name = "ip_address"
    type = "S"
  }

  tags = {
    Mode = "builder"
  }
}
