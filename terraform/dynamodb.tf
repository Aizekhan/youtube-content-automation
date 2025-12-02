# DynamoDB Tables - Infrastructure as Code

# 1. GeneratedContent - Main content storage
resource "aws_dynamodb_table" "generated_content" {
  name           = "GeneratedContent"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "content_id"

  attribute {
    name = "content_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "channel_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # GSI for user queries
  global_secondary_index {
    name            = "user_id-created_at-index"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI for channel queries
  global_secondary_index {
    name            = "channel_id-created_at-index"
    hash_key        = "channel_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI for video assembly lookup (WEEK 5.3 FIX)
  global_secondary_index {
    name            = "content_id-created_at-index"
    hash_key        = "content_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # Point-in-Time Recovery
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled = true
  }

  # Auto-cleanup old content (90 days)
  ttl {
    enabled        = true
    attribute_name = "ttl_expiration"
  }

  tags = {
    Name        = "GeneratedContent"
    Description = "YouTube automation generated content storage"
  }
}

# 2. ChannelConfigs - Channel configuration
resource "aws_dynamodb_table" "channel_configs" {
  name           = "ChannelConfigs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "channel_id"

  attribute {
    name = "channel_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "is_active"
    type = "N"
  }

  # GSI for user's active channels
  global_secondary_index {
    name            = "user_id-is_active-index"
    hash_key        = "user_id"
    range_key       = "is_active"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "ChannelConfigs"
    Description = "YouTube channel configurations"
  }
}

# 3. CostTracking - Cost tracking
resource "aws_dynamodb_table" "cost_tracking" {
  name           = "CostTracking"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "record_id"

  attribute {
    name = "record_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  # GSI for user cost queries
  global_secondary_index {
    name            = "user_id-date-index"
    hash_key        = "user_id"
    range_key       = "date"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  # Auto-cleanup old cost records (365 days)
  ttl {
    enabled        = true
    attribute_name = "ttl_expiration"
  }

  tags = {
    Name        = "CostTracking"
    Description = "AWS cost tracking for multi-tenant system"
  }
}

# 4. EC2InstanceLocks - EC2 lock management
resource "aws_dynamodb_table" "ec2_instance_locks" {
  name           = "EC2InstanceLocks"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "instance_id"

  attribute {
    name = "instance_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "EC2InstanceLocks"
    Description = "EC2 instance optimistic locking"
  }
}
