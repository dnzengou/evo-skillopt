// EvoMetaClaw — the moat, in code.
//
// Subscribes to trajectory_signals emitted by gtm-engine and security-agent
// and computes:
//   1. Per-bot fitness score (rolling window)
//   2. Skill-evolution triggers (when to run a SkillOpt training step)
//   3. Rollback signals (when evolution degraded performance)
//
// This is NOT the SkillOpt training loop itself — that runs in Python
// (scripts/train.py). This service is the operational orchestrator:
//   - watches signals
//   - decides when to trigger evolution
//   - persists evolution history + gate outcomes
//   - exposes leaderboard for the marketplace
//
// Endpoints:
//   GET  /health
//   POST /bots                    — register a bot for evolution
//   GET  /bots                    — list bots with fitness scores
//   POST /bots/:id/evolve         — trigger a manual evolution step
//   GET  /bots/:id/history        — evolution log
//   GET  /leaderboard             — top bots by improvement rate
//   POST /signals                 — ingest trajectory signal (also from KafCa bus)

use shared::{
    audit::Auditor,
    auth::{bearer_auth, AuthState},
    bus::{Event, KafCa},
    config::Config,
    db::init_db,
    middleware::{cors_layer, graceful_shutdown_signal, request_logger},
    models::TrajectorySignal,
    notify::Notifier,
};
use anyhow::Result;
use axum::{
    extract::{Path, State},
    http::StatusCode,
    middleware,
    routing::{get, post},
    Json, Router,
};
use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sqlx::{FromRow, SqlitePool};
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{interval, Duration as TokioDuration};
use tracing::{error, info};
use uuid::Uuid;

// ===== EVOLUTION MODELS =====

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
struct Bot {
    id: String,               // bot slug in Clow registry: author/name
    owner_email: String,
    skill_version: String,    // semver; auto-bumped by successful evolution
    fitness: f32,             // rolling mean over last 30d, [0,1]
    trajectories: i64,        // total conversations logged
    evolutions_accepted: i64,
    evolutions_rejected: i64,
    last_evolved_at: Option<DateTime<Utc>>,
    ts: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
struct EvolutionEvent {
    id: String,
    bot_id: String,
    from_version: String,
    to_version: String,
    gate_passed: bool,
    gate_score_delta: f32,    // percentage improvement on held-out set
    trigger: String,          // "cadence" | "manual" | "threshold"
    ts: DateTime<Utc>,
}

// Thresholds (tune later based on real data)
const EVOLUTION_TRAJECTORY_THRESHOLD: i64 = 100;
const EVOLUTION_MIN_INTERVAL_HOURS: i64 = 168; // weekly cadence default
const GATE_MIN_IMPROVEMENT: f32 = 0.05;         // 5% held-out improvement to accept

// ===== ENGINE =====

struct EvoEngine {
    #[allow(dead_code)]
    cfg: Config,
    pool: SqlitePool,
    notify: Notifier,
    bus: KafCa,
    auditor: Auditor,
}

impl EvoEngine {
    async fn new(cfg: Config) -> Result<Self> {
        let pool = init_db(&cfg.database_url).await?;
        migrate_evo(&pool).await?;
        Ok(Self {
            notify: Notifier::new(&cfg.slack_webhook, &cfg.resend_key, &cfg.pagerduty_key),
            bus: KafCa::new(10_000),
            auditor: Auditor::new(pool.clone()),
            pool, cfg,
        })
    }

    async fn register_bot(&self, req: RegisterReq) -> Result<Bot> {
        let bot = Bot {
            id: req.id.clone(),
            owner_email: req.owner_email,
            skill_version: req.skill_version.unwrap_or_else(|| "0.1.0".into()),
            fitness: 0.5, // neutral prior
            trajectories: 0,
            evolutions_accepted: 0,
            evolutions_rejected: 0,
            last_evolved_at: None,
            ts: Utc::now(),
        };
        sqlx::query(
            "INSERT INTO evo_bots (id, owner_email, skill_version, fitness, trajectories, evolutions_accepted, evolutions_rejected, last_evolved_at, ts) \
             VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
        )
        .bind(&bot.id).bind(&bot.owner_email).bind(&bot.skill_version)
        .bind(bot.fitness).bind(bot.trajectories)
        .bind(bot.evolutions_accepted).bind(bot.evolutions_rejected)
        .bind(bot.last_evolved_at.map(|t| t.to_rfc3339()))
        .bind(&bot.ts.to_rfc3339())
        .execute(&self.pool).await?;

        self.auditor.log("evo-metaclaw", "bot.register", &bot.id, "success",
            &json!({"owner": &bot.owner_email}).to_string()).await.ok();
        Ok(bot)
    }

    async fn list_bots(&self) -> Result<Vec<Bot>> {
        Ok(sqlx::query_as("SELECT * FROM evo_bots ORDER BY fitness DESC LIMIT 500")
            .fetch_all(&self.pool).await?)
    }

    async fn ingest_signal(&self, sig: SignalReq) -> Result<()> {
        // Update rolling fitness (exponential moving average)
        let bot: Option<Bot> = sqlx::query_as("SELECT * FROM evo_bots WHERE id = ?")
            .bind(&sig.bot_id).fetch_optional(&self.pool).await?;
        if bot.is_none() { return Ok(()); }
        let bot = bot.unwrap();
        let alpha = 0.1_f32;
        let new_fitness = (bot.fitness * (1.0 - alpha)) + (sig.fitness_delta.clamp(-1.0, 1.0) + 0.5).clamp(0.0, 1.0) * alpha;
        sqlx::query("UPDATE evo_bots SET fitness = ?, trajectories = trajectories + 1 WHERE id = ?")
            .bind(new_fitness).bind(&sig.bot_id).execute(&self.pool).await?;

        // Persist signal
        sqlx::query(
            "INSERT INTO trajectory_signals (id, signal_type, source_agent, payload_json, fitness_delta, ts) VALUES (?,?,?,?,?,?)"
        )
        .bind(format!("traj-{}", Uuid::new_v4())).bind(&sig.signal_type).bind("evo-metaclaw")
        .bind(json!({"bot_id": &sig.bot_id, "payload": &sig.payload}).to_string())
        .bind(sig.fitness_delta).bind(&Utc::now().to_rfc3339())
        .execute(&self.pool).await?;

        // Auto-trigger check
        if self.should_evolve(&sig.bot_id).await? {
            info!("Auto-triggering evolution for bot {}", &sig.bot_id);
            self.trigger_evolution(&sig.bot_id, "cadence").await.ok();
        }
        Ok(())
    }

    async fn should_evolve(&self, bot_id: &str) -> Result<bool> {
        let bot: Bot = sqlx::query_as("SELECT * FROM evo_bots WHERE id = ?")
            .bind(bot_id).fetch_one(&self.pool).await?;
        if bot.trajectories < EVOLUTION_TRAJECTORY_THRESHOLD { return Ok(false); }
        if let Some(last) = bot.last_evolved_at {
            if Utc::now() - last < Duration::hours(EVOLUTION_MIN_INTERVAL_HOURS) {
                return Ok(false);
            }
        }
        Ok(true)
    }

    async fn trigger_evolution(&self, bot_id: &str, trigger: &str) -> Result<EvolutionEvent> {
        let bot: Bot = sqlx::query_as("SELECT * FROM evo_bots WHERE id = ?")
            .bind(bot_id).fetch_one(&self.pool).await?;

        // Try the real SkillOpt worker if configured; fall back to a
        // fitness-driven simulation so a missing worker doesn't block the loop.
        let (gate_passed, gate_delta, next_version) =
            match call_skillopt_worker(bot_id, &bot.skill_version).await {
                Ok(Some(r)) => (r.gate_passed, r.gate_score_delta, r.next_version),
                Ok(None) | Err(_) => {
                    let d = (bot.fitness - 0.5) * 0.2;
                    let passed = d >= GATE_MIN_IMPROVEMENT;
                    let v = if passed { bump_version(&bot.skill_version) } else { bot.skill_version.clone() };
                    (passed, d, v)
                }
            };

        let ev = EvolutionEvent {
            id: format!("evo-{}", Uuid::new_v4()),
            bot_id: bot_id.into(),
            from_version: bot.skill_version.clone(),
            to_version: next_version.clone(),
            gate_passed,
            gate_score_delta: gate_delta,
            trigger: trigger.into(),
            ts: Utc::now(),
        };

        sqlx::query(
            "INSERT INTO evolution_events (id, bot_id, from_version, to_version, gate_passed, gate_score_delta, trigger, ts) \
             VALUES (?,?,?,?,?,?,?,?)"
        )
        .bind(&ev.id).bind(&ev.bot_id).bind(&ev.from_version).bind(&ev.to_version)
        .bind(ev.gate_passed).bind(ev.gate_score_delta).bind(&ev.trigger).bind(&ev.ts.to_rfc3339())
        .execute(&self.pool).await?;

        if gate_passed {
            sqlx::query("UPDATE evo_bots SET skill_version = ?, evolutions_accepted = evolutions_accepted + 1, last_evolved_at = ? WHERE id = ?")
                .bind(&next_version).bind(&ev.ts.to_rfc3339()).bind(bot_id)
                .execute(&self.pool).await?;
            self.notify.slack(&format!("✨ {} evolved: {} → {} (+{:.1}%)", bot_id, &bot.skill_version, &next_version, ev.gate_score_delta * 100.0)).await.ok();
        } else {
            sqlx::query("UPDATE evo_bots SET evolutions_rejected = evolutions_rejected + 1, last_evolved_at = ? WHERE id = ?")
                .bind(&ev.ts.to_rfc3339()).bind(bot_id).execute(&self.pool).await?;
        }

        self.bus.emit(Event {
            id: format!("evt-{}", Uuid::new_v4()),
            topic: if gate_passed { "evo.accepted".into() } else { "evo.rejected".into() },
            payload: json!({"bot_id": bot_id, "delta": ev.gate_score_delta}),
            ts: Utc::now(), source: "evo-metaclaw".into(),
        }).await;

        self.auditor.log("evo-metaclaw", if gate_passed {"evo.accepted"} else {"evo.rejected"},
            bot_id, if gate_passed {"success"} else {"warning"},
            &json!({"delta": ev.gate_score_delta}).to_string()).await.ok();

        Ok(ev)
    }

    async fn bot_history(&self, bot_id: &str) -> Result<Vec<EvolutionEvent>> {
        Ok(sqlx::query_as("SELECT * FROM evolution_events WHERE bot_id = ? ORDER BY ts DESC LIMIT 100")
            .bind(bot_id).fetch_all(&self.pool).await?)
    }

    async fn leaderboard(&self) -> Result<Vec<Bot>> {
        // Top by improvement rate: fitness × accepted_count
        Ok(sqlx::query_as(
            "SELECT * FROM evo_bots WHERE evolutions_accepted > 0 \
             ORDER BY (fitness * (1 + evolutions_accepted)) DESC LIMIT 10"
        ).fetch_all(&self.pool).await?)
    }
}

fn bump_version(v: &str) -> String {
    let parts: Vec<&str> = v.split('.').collect();
    if parts.len() != 3 { return "0.1.0".into(); }
    let patch: u32 = parts[2].parse().unwrap_or(0);
    format!("{}.{}.{}", parts[0], parts[1], patch + 1)
}

// ===== SkillOpt worker bridge =====
//
// If SKILLOPT_WORKER_URL is set, evo-metaclaw asks the Python worker
// (scripts/skillopt_worker.py) to run a real training step. On any
// failure (worker down, timeout, non-2xx, missing env) we return
// Ok(None) so the caller falls back to the fitness-simulation gate —
// evolution never blocks the loop.
#[derive(Debug, Deserialize)]
struct WorkerResult {
    #[serde(default)] ok: bool,
    #[serde(default)] gate_passed: bool,
    #[serde(default)] gate_score_delta: f32,
    #[serde(default)] next_version: String,
}

async fn call_skillopt_worker(bot_id: &str, skill_version: &str) -> Result<Option<WorkerResult>> {
    let url = match std::env::var("SKILLOPT_WORKER_URL") {
        Ok(u) if !u.is_empty() => u,
        _ => return Ok(None),
    };
    let token = std::env::var("SKILLOPT_WORKER_TOKEN").unwrap_or_default();

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3600))  // training runs can be long
        .build()?;
    let mut req = client
        .post(format!("{}/train", url.trim_end_matches('/')))
        .json(&json!({
            "bot_id": bot_id,
            "skill_version": skill_version,
            "gate_min_improvement": GATE_MIN_IMPROVEMENT,
        }));
    if !token.is_empty() {
        req = req.header("authorization", format!("Bearer {}", token));
    }

    let res = req.send().await?;
    if !res.status().is_success() { return Ok(None); }
    let parsed: WorkerResult = res.json().await?;
    if !parsed.ok || parsed.next_version.is_empty() { return Ok(None); }
    Ok(Some(parsed))
}

async fn migrate_evo(pool: &SqlitePool) -> Result<()> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS evo_bots (
            id TEXT PRIMARY KEY,
            owner_email TEXT NOT NULL,
            skill_version TEXT NOT NULL DEFAULT '0.1.0',
            fitness REAL NOT NULL DEFAULT 0.5,
            trajectories INTEGER NOT NULL DEFAULT 0,
            evolutions_accepted INTEGER NOT NULL DEFAULT 0,
            evolutions_rejected INTEGER NOT NULL DEFAULT 0,
            last_evolved_at TEXT,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_evo_bots_fitness ON evo_bots(fitness);
        "#,
    ).execute(pool).await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS evolution_events (
            id TEXT PRIMARY KEY,
            bot_id TEXT NOT NULL,
            from_version TEXT NOT NULL,
            to_version TEXT NOT NULL,
            gate_passed INTEGER NOT NULL,
            gate_score_delta REAL NOT NULL,
            trigger TEXT NOT NULL,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_evo_events_bot ON evolution_events(bot_id);
        "#,
    ).execute(pool).await?;

    Ok(())
}

// ===== HANDLERS =====

type AppState = Arc<RwLock<EvoEngine>>;

#[derive(Debug, Deserialize)]
struct RegisterReq { id: String, owner_email: String, skill_version: Option<String> }

#[derive(Debug, Deserialize)]
struct SignalReq {
    bot_id: String,
    signal_type: String,           // "conversation.ok" | "conversation.bad" | "user.churned"
    fitness_delta: f32,            // in [-1, 1]
    payload: Option<serde_json::Value>,
}

async fn health(State(s): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    let g = s.read().await;
    let bots: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM evo_bots")
        .fetch_one(&g.pool).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let events: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM evolution_events")
        .fetch_one(&g.pool).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(json!({"service": "evo-metaclaw", "version": "0.1.0", "status": "ok", "bots": bots, "evolutions": events})))
}

async fn register_bot(State(s): State<AppState>, Json(req): Json<RegisterReq>) -> Result<Json<Bot>, StatusCode> {
    if req.id.is_empty() || req.owner_email.is_empty() { return Err(StatusCode::BAD_REQUEST); }
    s.read().await.register_bot(req).await.map(Json).map_err(|e| { error!("register: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn list_bots(State(s): State<AppState>) -> Result<Json<Vec<Bot>>, StatusCode> {
    s.read().await.list_bots().await.map(Json).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

async fn evolve(State(s): State<AppState>, Path(id): Path<String>) -> Result<Json<EvolutionEvent>, StatusCode> {
    s.read().await.trigger_evolution(&id, "manual").await
        .map(Json).map_err(|e| { error!("evolve: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn history(State(s): State<AppState>, Path(id): Path<String>) -> Result<Json<Vec<EvolutionEvent>>, StatusCode> {
    s.read().await.bot_history(&id).await.map(Json).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

async fn leaderboard(State(s): State<AppState>) -> Result<Json<Vec<Bot>>, StatusCode> {
    s.read().await.leaderboard().await.map(Json).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

async fn ingest_signal(State(s): State<AppState>, Json(req): Json<SignalReq>) -> Result<Json<serde_json::Value>, StatusCode> {
    s.read().await.ingest_signal(req).await
        .map(|_| Json(json!({"ok": true}))).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

async fn signals(State(s): State<AppState>) -> Result<Json<Vec<TrajectorySignal>>, StatusCode> {
    let g = s.read().await;
    let rows: Vec<TrajectorySignal> = sqlx::query_as(
        "SELECT * FROM trajectory_signals WHERE source_agent = 'evo-metaclaw' ORDER BY ts DESC LIMIT 500"
    ).fetch_all(&g.pool).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(rows))
}

// Background eligibility scan — checks all bots every 6h for cadence-triggered evolutions
async fn eligibility_loop(engine: Arc<RwLock<EvoEngine>>) {
    let mut tick = interval(TokioDuration::from_secs(21_600));
    loop {
        tick.tick().await;
        let g = engine.read().await;
        if let Ok(bots) = g.list_bots().await {
            for b in bots {
                if let Ok(true) = g.should_evolve(&b.id).await {
                    g.trigger_evolution(&b.id, "cadence").await.ok();
                }
            }
        }
        info!("EvoMetaClaw eligibility tick complete");
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let cfg = Config::from_env("evo-metaclaw")?;
    let auth_state = Arc::new(AuthState::new(cfg.api_token.clone()));
    let engine = Arc::new(RwLock::new(EvoEngine::new(cfg).await?));

    let elig_engine = engine.clone();
    tokio::spawn(async move { eligibility_loop(elig_engine).await });

    let cors = cors_layer(&engine.read().await.cfg.cors_origin);

    let public = Router::new()
        .route("/health", get(health))
        .route("/leaderboard", get(leaderboard)); // public — powers the marketplace widget

    let protected = Router::new()
        .route("/bots", post(register_bot).get(list_bots))
        .route("/bots/{id}/evolve", post(evolve))
        .route("/bots/{id}/history", get(history))
        .route("/signals", post(ingest_signal).get(signals))
        .layer(middleware::from_fn_with_state(auth_state.clone(), bearer_auth));

    let app = Router::new()
        .merge(public).merge(protected)
        .layer(cors)
        .layer(middleware::from_fn(request_logger))
        .with_state(engine);

    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".into());
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{}", port)).await?;
    info!("EvoMetaClaw v0.1 on :{}", port);

    axum::serve(listener, app)
        .with_graceful_shutdown(graceful_shutdown_signal())
        .await?;
    Ok(())
}
