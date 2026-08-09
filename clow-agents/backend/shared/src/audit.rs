use crate::models::AuditLog;
use anyhow::Result;
use chrono::Utc;
use sqlx::SqlitePool;
use tracing::debug;

pub struct Auditor {
    pool: SqlitePool,
}

impl Auditor {
    pub fn new(pool: SqlitePool) -> Self {
        Self { pool }
    }

    pub async fn log(&self, agent: &str, action: &str, target: &str, result: &str, details: &str) -> Result<()> {
        let id = uuid::Uuid::new_v4().to_string();
        let ts = Utc::now().to_rfc3339();

        sqlx::query(
            "INSERT INTO audit_logs (id, agent, action, target, result, details, ts) VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        .bind(&id)
        .bind(agent)
        .bind(action)
        .bind(target)
        .bind(result)
        .bind(details)
        .bind(&ts)
        .execute(&self.pool)
        .await?;

        debug!("AUDIT {} | {} | {} | {}", agent, action, target, result);
        Ok(())
    }

    pub async fn list(&self, agent: Option<&str>, limit: i64) -> Result<Vec<AuditLog>> {
        let rows = match agent {
            Some(a) => {
                sqlx::query_as::<_, AuditLog>(
                    "SELECT * FROM audit_logs WHERE agent = ? ORDER BY ts DESC LIMIT ?"
                )
                .bind(a)
                .bind(limit)
                .fetch_all(&self.pool)
                .await?
            }
            None => {
                sqlx::query_as::<_, AuditLog>(
                    "SELECT * FROM audit_logs ORDER BY ts DESC LIMIT ?"
                )
                .bind(limit)
                .fetch_all(&self.pool)
                .await?
            }
        };
        Ok(rows)
    }

    pub async fn count_by_action(&self, agent: &str) -> Result<Vec<(String, i64)>> {
        let rows: Vec<(String, i64)> = sqlx::query_as(
            "SELECT action, COUNT(*) as cnt FROM audit_logs WHERE agent = ? GROUP BY action"
        )
        .bind(agent)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }
}
