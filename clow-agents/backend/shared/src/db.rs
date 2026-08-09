use anyhow::Result;
use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use tracing::info;

pub async fn init_db(database_url: &str) -> Result<Pool<Sqlite>> {
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(database_url)
        .await?;

    info!("SQLite connected: {}", database_url);
    migrate(&pool).await?;
    Ok(pool)
}

async fn migrate(pool: &Pool<Sqlite>) -> Result<()> {
    // GTM tables
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            domain TEXT NOT NULL,
            persona TEXT NOT NULL,
            revenue_stream TEXT NOT NULL,
            score REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'new',
            mrr REAL NOT NULL DEFAULT 0,
            arr REAL NOT NULL DEFAULT 0,
            lifetime_value REAL NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'inbound',
            metadata TEXT NOT NULL DEFAULT '{}',
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_accounts_persona ON accounts(persona);
        CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
        "#,
    )
    .execute(pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS deals (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            persona TEXT NOT NULL,
            revenue_stream TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'discovery',
            value REAL NOT NULL DEFAULT 0,
            probability REAL NOT NULL DEFAULT 0.2,
            expected_close TEXT NOT NULL,
            mrr REAL NOT NULL DEFAULT 0,
            ts TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        );
        CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
        CREATE INDEX IF NOT EXISTS idx_deals_account ON deals(account_id);
        "#,
    )
    .execute(pool)
    .await?;

    // Security tables
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS findings (
            id TEXT PRIMARY KEY,
            scan_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            target TEXT NOT NULL,
            vuln_type TEXT NOT NULL,
            evidence TEXT NOT NULL,
            cvss REAL NOT NULL DEFAULT 0,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
        CREATE INDEX IF NOT EXISTS idx_findings_target ON findings(target);
        CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
        "#,
    )
    .execute(pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS scan_results (
            scan_id TEXT PRIMARY KEY,
            target TEXT NOT NULL,
            status TEXT NOT NULL,
            findings_json TEXT NOT NULL DEFAULT '[]',
            severity_counts_json TEXT NOT NULL DEFAULT '{}',
            duration_ms INTEGER NOT NULL DEFAULT 0,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scan_target ON scan_results(target);
        "#,
    )
    .execute(pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS ecosystem_reports (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            targets_json TEXT NOT NULL DEFAULT '[]',
            total_findings INTEGER NOT NULL DEFAULT 0,
            critical_findings INTEGER NOT NULL DEFAULT 0,
            compliance_score REAL NOT NULL DEFAULT 100
        );
        "#,
    )
    .execute(pool)
    .await?;

    // Audit + trajectory tables
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            result TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '{}',
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_logs(agent);
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
        CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_logs(ts);
        "#,
    )
    .execute(pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS trajectory_signals (
            id TEXT PRIMARY KEY,
            signal_type TEXT NOT NULL,
            source_agent TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            fitness_delta REAL NOT NULL DEFAULT 0,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_traj_type ON trajectory_signals(signal_type);
        CREATE INDEX IF NOT EXISTS idx_traj_ts ON trajectory_signals(ts);
        "#,
    )
    .execute(pool)
    .await?;

    info!("Migrations complete");
    Ok(())
}
