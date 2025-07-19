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


resource "aws_iam_role" "ascii-lambda-execution-role" {
  name = "ascii_lambda_execution_role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
    }

  )
}


resource "aws_lambda_function" "ascii-lambda" {
  function_name = "ascii-generator-function"
  role          = aws_iam_role.ascii-lambda-execution-role.arn
  handler       = "lambda_function.handler"

  s3_bucket = aws_s3_bucket.ascii.id
  s3_key    = "ascii-lambda.zip"

  environment {
    variables = {
      GEMINI_API_KEY = var.gemini_api_key
    }
  }

  runtime       = "python3.12"
  architectures = ["x86_64"]
  timeout       = 300
}

data "aws_iam_policy_document" "lambda-extra-policies-document" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem"
    ]
    resources = [
      aws_dynamodb_table.rate-limit-table.arn
    ]
    effect = "Allow"
    sid    = "allowDynamoDBAccess"
  }

  statement {
    actions = [
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.ascii.arn,
      "${aws_s3_bucket.ascii.arn}/*"
    ]
    effect = "Allow"
    sid    = "allowS3Access"
  }

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:PutLogEvents",
      "logs:CreateLogStream"
    ]
    resources = ["*"]
    effect    = "Allow"
    sid       = "allowCloudWatchLogsAccess"
  }
}

resource "aws_iam_policy" "lambda-extra-policies" {
  name = "ascii-lambda-extra-policies"

  policy = data.aws_iam_policy_document.lambda-extra-policies-document.json
}

resource "aws_iam_role_policy_attachment" "ascii-lambda-policy-attachment" {
  role       = aws_iam_role.ascii-lambda-execution-role.name
  policy_arn = aws_iam_policy.lambda-extra-policies.arn
}

resource "aws_lambda_function_url" "ascii-lambda-url" {
  function_name      = aws_lambda_function.ascii-lambda.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST"]
    allow_headers     = ["*"]
    expose_headers    = []
    max_age           = 86400
  }
}
