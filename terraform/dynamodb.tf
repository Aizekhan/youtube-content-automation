# DynamoDB Tables для YouTube Content Automation

# =====================================
# AIPromptConfigs - Конфігурації AI агентів
# =====================================
resource "aws_dynamodb_table" "ai_prompt_configs" {
  name           = "AIPromptConfigs"
  billing_mode   = "PAY_PER_REQUEST" # On-demand pricing
  hash_key       = "agent_id"

  attribute {
    name = "agent_id"
    type = "S"
  }

  tags = {
    Name        = "AIPromptConfigs"
    Description = "Зберігає конфігурації для AI агентів (Theme Agent, Narrative Architect)"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

# =====================================
# ChannelConfigs - Конфігурації каналів
# =====================================
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

  # GSI для пошуку за channel_id
  global_secondary_index {
    name            = "channel_id-index"
    hash_key        = "channel_id"
    projection_type = "ALL"
  }

  tags = {
    Name        = "ChannelConfigs"
    Description = "Зберігає конфігурації YouTube каналів для генерації контенту"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

# =====================================
# GeneratedVideos - Згенеровані відео
# =====================================
resource "aws_dynamodb_table" "generated_videos" {
  name           = "GeneratedVideos"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "video_id"
  range_key      = "created_at"

  attribute {
    name = "video_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "channel_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # GSI для пошуку відео по каналу
  global_secondary_index {
    name            = "channel_id-index"
    hash_key        = "channel_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI для пошуку по статусу
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = {
    Name        = "GeneratedVideos"
    Description = "Зберігає інформацію про згенеровані відео"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  # TTL для автоматичного видалення старих записів (опціонально)
  # ttl {
  #   attribute_name = "expires_at"
  #   enabled        = true
  # }
}

# =====================================
# ContentQueue - Черга контенту для генерації (опціонально)
# =====================================
resource "aws_dynamodb_table" "content_queue" {
  name           = "ContentQueue"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "queue_id"
  range_key      = "timestamp"

  attribute {
    name = "queue_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "channel_id"
    type = "S"
  }

  # GSI для пошуку по каналу
  global_secondary_index {
    name            = "channel_id-index"
    hash_key        = "channel_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  tags = {
    Name        = "ContentQueue"
    Description = "Черга завдань для генерації контенту"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  # TTL для автоматичного видалення виконаних завдань
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}
