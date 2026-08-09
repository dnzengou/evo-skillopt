use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;

// ===== GTM MODELS =====

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Account {
    pub id: String,
    pub name: String,
    pub email: String,
    pub domain: String,
    pub persona: String,
    pub revenue_stream: String,
    pub score: f32,
    pub status: String,
    pub mrr: f32,
    pub arr: f32,
    pub lifetime_value: f32,
    pub source: String,
    pub metadata: String, // JSON serialized HashMap
    pub ts: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Deal {
    pub id: String,
    pub account_id: String,
    pub persona: String,
    pub revenue_stream: String,
    pub stage: String,
    pub value: f32,
    pub probability: f32,
    pub expected_close: DateTime<Utc>,
    pub mrr: f32,
    pub ts: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineForecast {
    pub total_deals: i64,
    pub total_value: f32,
    pub weighted_forecast: f32,
    pub mrr: f32,
    pub arr: f32,
    pub by_persona: String, // JSON
    pub by_stream: String,  // JSON
    pub by_stage: String,   // JSON
}

// ===== SECURITY MODELS =====

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Finding {
    pub id: String,
    pub scan_id: String,
    pub severity: String,
    pub target: String,
    pub vuln_type: String,
    pub evidence: String,
    pub cvss: f32,
    pub ts: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct ScanResult {
    pub scan_id: String,
    pub target: String,
    pub status: String,
    pub findings_json: String,
    pub severity_counts_json: String,
    pub duration_ms: i64,
    pub ts: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct EcosystemReport {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    pub targets_json: String,
    pub total_findings: i64,
    pub critical_findings: i64,
    pub compliance_score: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct TargetHealth {
    pub domain: String,
    pub up: bool,
    pub response_time_ms: i64,
    pub findings: i64,
    pub ssl_valid: bool,
}

// ===== AUDIT MODELS =====

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct AuditLog {
    pub id: String,
    pub agent: String,      // "gtm-engine" | "security-agent"
    pub action: String,     // "account.ingest" | "deal.advance" | "scan.run" etc
    pub target: String,     // account_id | deal_id | target_domain
    pub result: String,     // "success" | "failure" | "warning"
    pub details: String,    // JSON payload
    pub ts: DateTime<Utc>,
}

// ===== TRAJECTORY / EVOLUTION MODELS =====

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct TrajectorySignal {
    pub id: String,
    pub signal_type: String, // "score.accepted" | "score.rejected" | "deal.won" | "deal.lost" | "finding.critical"
    pub source_agent: String,
    pub payload_json: String,
    pub fitness_delta: f32,
    pub ts: DateTime<Utc>,
}
