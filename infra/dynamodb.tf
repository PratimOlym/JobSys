# ── DynamoDB Tables ────────────────────────────────────────────────────────────

# Jobs table — stores all job records
resource "aws_dynamodb_table" "jobs" {
  name         = "${var.project_name}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # GSI for querying jobs by status
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-jobs"
  }
}

# Config table — stores system configuration (job sources, user profile, etc.)
resource "aws_dynamodb_table" "config" {
  name         = "${var.project_name}-config"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "config_key"

  attribute {
    name = "config_key"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-config"
  }
}

# Token Usage table — one row per LLM API call for cost monitoring
resource "aws_dynamodb_table" "token_usage" {
  name         = "${var.project_name}-token-usage"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "record_id"
  range_key    = "timestamp"

  attribute {
    name = "record_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "provider"
    type = "S"
  }

  # GSI: query all records for a given provider sorted by time
  global_secondary_index {
    name            = "provider-timestamp-index"
    hash_key        = "provider"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # Automatically delete records older than 90 days to manage storage costs
  ttl {
    attribute_name = "ttl_epoch"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-token-usage"
  }
}
