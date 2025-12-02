# DynamoDB Tables - Production Schemas (Auto-generated from AWS)

# 1. GeneratedContent - Main content storage
resource "aws_dynamodb_table" "generated_content" {
  name           = "GeneratedContent"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "channel_id"
  range_key      = "created_at"

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

  # GSI for video assembly lookup
  global_secondary_index {
    name            = "content_id-created_at-index"
    hash_key        = "content_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  ttl {
    enabled = false
  }

  tags = {
    Name    = "GeneratedContent"
    Project = "n8n-creator"
    Purpose = "content-storage"
  }
}

# 2. ChannelConfigs - Channel configuration
resource "aws_dynamodb_table" "channel_configs" {
  name           = "ChannelConfigs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "config_id"

  attribute {
    name = "config_id"
    type = "S"
  }

  attribute {
    name = "channel_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "channel_id-index"
    hash_key        = "channel_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "user_id-channel_id-index"
    hash_key        = "user_id"
    range_key       = "channel_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  ttl {
    enabled = false
  }

  tags = {
    Name = "ChannelConfigs"
  }
}

# 3. CostTracking - Cost tracking
resource "aws_dynamodb_table" "cost_tracking" {
  name           = "CostTracking"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "date"
  range_key      = "timestamp"

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

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

  ttl {
    enabled = false
  }

  tags = {
    Name = "CostTracking"
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
    Name = "EC2InstanceLocks"
  }
}
