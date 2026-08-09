// GTM Engine — Clow bots ecosystem
// Automates ARM (Adoption / Retention / Monetization):
//   - Waitlist ingest → lead score (ICP fit)
//   - Deal pipeline: Free → Pro → Teams → Enterprise
//   - MRR forecast (weighted pipeline)
//   - Emits trajectory signals for evo-metaclaw to learn from
//
// Endpoints (all bearer-auth except /health):
//   GET  /health
//   POST /accounts              — ingest waitlist / lead
//   GET  /accounts              — list, sorted by score
//   POST /deals                 — create deal from account
//   POST /deals/:id/advance     — move deal to next stage
//   GET  /pipeline/forecast     — weighted MRR forecast
//   GET  /audit                 — audit log tail
//   GET  /events                — recent bus events

use shared::{
    audit::Auditor,
    auth::{bearer_auth, AuthState},
    bus::{Event, KafCa},
    config::Config,
    db::init_db,
    middleware::{cors_layer, graceful_shutdown_signal, request_logger},
    models::{Account, AuditLog, Deal, PipelineForecast, TrajectorySignal},
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
use chrono::{Duration, Utc};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sqlx::SqlitePool;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{interval, Duration as TokioDuration};
use tracing::{error, info};
use uuid::Uuid;

// ===== ICP MODEL (Clow-specific) =====
//
// The three Clow ICPs from MARKETING.md:
//   edge-builder      — indie dev / maker, hardware-owning
//   automation-dev    — Go/backend dev, chatbot builder
//   enterprise-edge   — mid-market IT/Ops, on-prem AI
//
// Scoring signals we can extract from waitlist metadata:
//   email domain    → free-mail vs corporate → persona hint
//   source          → github / twitter / producthunt / hn / discord
//   plan interest   → free / pro / teams / enterprise
//   UA hints        → hardware/dev tools mentions

const STAGES: &[&str] = &["discovery", "activated", "pro", "teams", "enterprise", "won", "lost"];

fn stage_probability(stage: &str) -> f32 {
    match stage {
        "discovery" => 0.10,
        "activated" => 0.30,     // deployed ≥1 bot
        "pro" => 0.60,           // subscribed Pro
        "teams" => 0.75,
        "enterprise" => 0.85,
        "won" => 1.0,
        "lost" => 0.0,
        _ => 0.10,
    }
}

fn stage_mrr(stage: &str) -> f32 {
    match stage {
        "pro" => 9.0,
        "teams" => 29.0,
        "enterprise" => 499.0,
        _ => 0.0,
    }
}

// ===== INGEST =====

#[derive(Debug, Clone, Serialize, Deserialize)]
struct IngestReq {
    email: String,
    source: Option<String>,        // twitter | github | producthunt | hn | discord | direct
    plan: Option<String>,          // free | pro | teams | enterprise
    domain_hint: Option<String>,   // optional: user-supplied company domain
    ua: Option<String>,
    metadata: Option<HashMap<String, String>>,
}

fn extract_domain(email: &str) -> String {
    email.split('@').nth(1).unwrap_or("").to_lowercase()
}

fn is_free_mail(domain: &str) -> bool {
    matches!(
        domain,
        "gmail.com" | "yahoo.com" | "outlook.com" | "hotmail.com"
            | "proton.me" | "protonmail.com" | "icloud.com" | "aol.com" | "mail.com"
    )
}

fn classify_persona(domain: &str, source: &str, ua: &str) -> String {
    let ua_l = ua.to_lowercase();
    // Enterprise signal: corporate domain + not source=twitter
    if !is_free_mail(domain) && domain.len() > 4 {
        if source == "producthunt" || source == "linkedin" {
            return "enterprise-edge".into();
        }
        if ua_l.contains("windows") || ua_l.contains("mac os") {
            return "automation-dev".into();
        }
        return "enterprise-edge".into();
    }
    // Hardware / edge signal
    if ua_l.contains("linux") || ua_l.contains("armv") || source == "github" || source == "hn" {
        return "edge-builder".into();
    }
    // Default
    "automation-dev".into()
}

fn score_account(a: &IngestScoring) -> f32 {
    let mut s: f32 = 0.0;
    // Domain quality
    s += if a.is_free { 5.0 } else { 25.0 };
    // Source quality (intent signal)
    s += match a.source.as_str() {
        "producthunt" => 20.0,
        "github" => 18.0,
        "hn" => 15.0,
        "twitter" => 12.0,
        "discord" => 10.0,
        _ => 6.0,
    };
    // Stated plan interest
    s += match a.plan.as_str() {
        "enterprise" => 40.0,
        "teams" => 25.0,
        "pro" => 15.0,
        _ => 5.0,
    };
    // Persona-specific bonus
    s += match a.persona.as_str() {
        "enterprise-edge" => 15.0,
        "automation-dev" => 8.0,
        _ => 3.0,
    };
    s.min(100.0)
}

struct IngestScoring {
    is_free: bool,
    source: String,
    plan: String,
    persona: String,
}

// ===== ENGINE =====

struct GtmEngine {
    cfg: Config,
    pool: SqlitePool,
    notify: Notifier,
    bus: KafCa,
    auditor: Auditor,
}

impl GtmEngine {
    async fn new(cfg: Config) -> Result<Self> {
        let pool = init_db(&cfg.database_url).await?;
        let bus = KafCa::new(10_000);
        let notify = Notifier::new(&cfg.slack_webhook, &cfg.resend_key, &cfg.pagerduty_key);
        let auditor = Auditor::new(pool.clone());
        Ok(Self { cfg, pool, notify, bus, auditor })
    }

    async fn ingest(&self, req: IngestReq) -> Result<Account> {
        let email = req.email.trim().to_lowercase();
        let source = req.source.unwrap_or_else(|| "direct".into());
        let plan = req.plan.unwrap_or_else(|| "free".into());
        let ua = req.ua.unwrap_or_default();
        let domain = req.domain_hint.unwrap_or_else(|| extract_domain(&email));
        let is_free = is_free_mail(&domain);
        let persona = classify_persona(&domain, &source, &ua);
        let score = score_account(&IngestScoring {
            is_free,
            source: source.clone(),
            plan: plan.clone(),
            persona: persona.clone(),
        });

        // Revenue stream mapping (Clow-specific)
        let revenue_stream = match plan.as_str() {
            "enterprise" => "enterprise-subscription",
            "teams" => "teams-subscription",
            "pro" => "pro-subscription",
            _ => "marketplace-fees", // free users still generate GMV via bot deploys
        }
        .to_string();

        let id = format!("acc-{}", Uuid::new_v4());
        let name = email.split('@').next().unwrap_or("unknown").to_string();
        let metadata = serde_json::to_string(&req.metadata.unwrap_or_default())?;
        let ts = Utc::now();

        sqlx::query(
            "INSERT INTO accounts (id, name, email, domain, persona, revenue_stream, score, status, mrr, arr, lifetime_value, source, metadata, ts) \
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        )
        .bind(&id).bind(&name).bind(&email).bind(&domain)
        .bind(&persona).bind(&revenue_stream).bind(score)
        .bind("new").bind(0.0f32).bind(0.0f32).bind(0.0f32)
        .bind(&source).bind(&metadata).bind(&ts.to_rfc3339())
        .execute(&self.pool).await?;

        // Alert on hot leads: enterprise-edge + score >= 70
        if persona == "enterprise-edge" && score >= 70.0 {
            self.notify
                .slack(&format!("🔥 Hot lead: {} · score {:.0} · plan {}", email, score, plan))
                .await
                .ok();
        }

        self.auditor
            .log("gtm-engine", "account.ingest", &id, "success",
                &json!({"email": &email, "score": score, "persona": &persona}).to_string())
            .await.ok();

        // Emit trajectory signal for evo-metaclaw
        self.bus.emit(Event {
            id: format!("evt-{}", Uuid::new_v4()),
            topic: "gtm.account.ingested".into(),
            payload: json!({"account_id": &id, "persona": &persona, "score": score, "source": &source}),
            ts: Utc::now(),
            source: "gtm-engine".into(),
        }).await;

        self.record_signal(
            if score >= 70.0 { "score.accepted" } else { "score.rejected" },
            &json!({"account_id": &id, "score": score, "persona": &persona}),
            score / 100.0 - 0.5, // fitness_delta: [-0.5, 0.5]
        ).await?;

        Ok(Account {
            id, name, email, domain, persona, revenue_stream,
            score, status: "new".into(), mrr: 0.0, arr: 0.0, lifetime_value: 0.0,
            source, metadata, ts,
        })
    }

    async fn list_accounts(&self, limit: i64) -> Result<Vec<Account>> {
        let rows: Vec<Account> = sqlx::query_as(
            "SELECT * FROM accounts ORDER BY score DESC LIMIT ?"
        ).bind(limit).fetch_all(&self.pool).await?;
        Ok(rows)
    }

    async fn create_deal(&self, req: CreateDealReq) -> Result<Deal> {
        // Load account
        let acc: Account = sqlx::query_as("SELECT * FROM accounts WHERE id = ?")
            .bind(&req.account_id).fetch_one(&self.pool).await?;

        let stage = req.stage.unwrap_or_else(|| "discovery".into());
        let probability = stage_probability(&stage);
        let mrr = stage_mrr(&stage);
        let value = mrr * 12.0; // 1-year ARR

        let id = format!("deal-{}", Uuid::new_v4());
        let expected_close = Utc::now() + Duration::days(45);
        let ts = Utc::now();

        sqlx::query(
            "INSERT INTO deals (id, account_id, persona, revenue_stream, stage, value, probability, expected_close, mrr, ts) \
             VALUES (?,?,?,?,?,?,?,?,?,?)",
        )
        .bind(&id).bind(&acc.id).bind(&acc.persona).bind(&acc.revenue_stream)
        .bind(&stage).bind(value).bind(probability)
        .bind(&expected_close.to_rfc3339()).bind(mrr).bind(&ts.to_rfc3339())
        .execute(&self.pool).await?;

        self.auditor.log("gtm-engine", "deal.create", &id, "success",
            &json!({"account_id": &acc.id, "stage": &stage, "value": value}).to_string()).await.ok();

        Ok(Deal {
            id, account_id: acc.id, persona: acc.persona, revenue_stream: acc.revenue_stream,
            stage, value, probability, expected_close, mrr, ts,
        })
    }

    async fn advance_deal(&self, deal_id: &str) -> Result<Deal> {
        let deal: Deal = sqlx::query_as("SELECT * FROM deals WHERE id = ?")
            .bind(deal_id).fetch_one(&self.pool).await?;

        let cur_idx = STAGES.iter().position(|s| *s == deal.stage.as_str()).unwrap_or(0);
        let next_stage = STAGES.get(cur_idx + 1).unwrap_or(&"won");
        let probability = stage_probability(next_stage);
        let mrr = stage_mrr(next_stage);
        let value = mrr * 12.0;

        sqlx::query(
            "UPDATE deals SET stage = ?, probability = ?, mrr = ?, value = ?, ts = ? WHERE id = ?"
        )
        .bind(next_stage).bind(probability).bind(mrr).bind(value)
        .bind(&Utc::now().to_rfc3339()).bind(deal_id)
        .execute(&self.pool).await?;

        // Won deals: update account MRR + emit high-value signal
        if next_stage == &"won" {
            sqlx::query("UPDATE accounts SET status = 'customer', mrr = ?, arr = ?, lifetime_value = ? WHERE id = ?")
                .bind(mrr).bind(mrr * 12.0).bind(mrr * 24.0) // 2yr LTV placeholder
                .bind(&deal.account_id).execute(&self.pool).await?;

            self.notify.slack(&format!("💰 Deal won: {} · ${:.0} MRR", deal_id, mrr)).await.ok();
            self.record_signal("deal.won", &json!({"deal_id": deal_id, "mrr": mrr}), 1.0).await?;
        } else if next_stage == &"lost" {
            self.record_signal("deal.lost", &json!({"deal_id": deal_id}), -1.0).await?;
        }

        self.auditor.log("gtm-engine", "deal.advance", deal_id, "success",
            &json!({"from": &deal.stage, "to": next_stage}).to_string()).await.ok();

        Ok(Deal { stage: next_stage.to_string(), probability, mrr, value, ..deal })
    }

    async fn forecast(&self) -> Result<PipelineForecast> {
        let deals: Vec<Deal> = sqlx::query_as("SELECT * FROM deals WHERE stage NOT IN ('won','lost')")
            .fetch_all(&self.pool).await?;

        let total_deals = deals.len() as i64;
        let total_value: f32 = deals.iter().map(|d| d.value).sum();
        let weighted_forecast: f32 = deals.iter().map(|d| d.value * d.probability).sum();
        let mrr: f32 = deals.iter().map(|d| d.mrr * d.probability).sum();
        let arr = mrr * 12.0;

        let mut by_persona: HashMap<String, f32> = HashMap::new();
        let mut by_stream: HashMap<String, f32> = HashMap::new();
        let mut by_stage: HashMap<String, f32> = HashMap::new();
        for d in &deals {
            *by_persona.entry(d.persona.clone()).or_default() += d.value * d.probability;
            *by_stream.entry(d.revenue_stream.clone()).or_default() += d.value * d.probability;
            *by_stage.entry(d.stage.clone()).or_default() += d.value * d.probability;
        }

        Ok(PipelineForecast {
            total_deals, total_value, weighted_forecast, mrr, arr,
            by_persona: serde_json::to_string(&by_persona)?,
            by_stream:  serde_json::to_string(&by_stream)?,
            by_stage:   serde_json::to_string(&by_stage)?,
        })
    }

    async fn record_signal(&self, signal_type: &str, payload: &serde_json::Value, fitness_delta: f32) -> Result<()> {
        let id = format!("traj-{}", Uuid::new_v4());
        sqlx::query(
            "INSERT INTO trajectory_signals (id, signal_type, source_agent, payload_json, fitness_delta, ts) VALUES (?,?,?,?,?,?)"
        )
        .bind(&id).bind(signal_type).bind("gtm-engine")
        .bind(payload.to_string()).bind(fitness_delta).bind(&Utc::now().to_rfc3339())
        .execute(&self.pool).await?;
        Ok(())
    }

    // Daily nurture tick — flags dormant leads for re-engagement.
    // Free function (not method) because `self: Arc<RwLock<Self>>` is not a
    // valid Rust receiver — only `Arc<Self>` is. Call site: main() does
    // `tokio::spawn(async move { GtmEngine::nurture_loop(state).await })`.
    async fn nurture_loop(state: Arc<RwLock<Self>>) {
        let mut tick = interval(TokioDuration::from_secs(86_400));
        loop {
            tick.tick().await;
            let g = state.read().await;
            let cutoff = (Utc::now() - Duration::days(14)).to_rfc3339();
            match sqlx::query_scalar::<_, i64>(
                "SELECT COUNT(*) FROM accounts WHERE status = 'new' AND ts < ?"
            ).bind(&cutoff).fetch_one(&g.pool).await {
                Ok(n) if n > 0 => {
                    g.notify.slack(&format!("🌙 {} dormant leads (>14d, no deal). Time to nurture.", n)).await.ok();
                    let _ = g.record_signal("nurture.dormant", &json!({"count": n}), -0.2).await;
                }
                _ => {}
            }
            info!("GTM nurture tick complete");
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CreateDealReq {
    account_id: String,
    stage: Option<String>,
}

// ===== HANDLERS =====

type AppState = Arc<RwLock<GtmEngine>>;

async fn health(State(s): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    let g = s.read().await;
    let acc: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM accounts")
        .fetch_one(&g.pool).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let deals: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM deals")
        .fetch_one(&g.pool).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(json!({
        "service": "gtm-engine", "version": "1.0.0", "status": "ok",
        "accounts": acc, "deals": deals,
    })))
}

async fn ingest_account(State(s): State<AppState>, Json(req): Json<IngestReq>) -> Result<Json<Account>, StatusCode> {
    if req.email.trim().is_empty() { return Err(StatusCode::BAD_REQUEST); }
    let g = s.read().await;
    g.ingest(req).await.map(Json).map_err(|e| { error!("ingest: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn list_accounts(State(s): State<AppState>) -> Result<Json<Vec<Account>>, StatusCode> {
    let g = s.read().await;
    g.list_accounts(500).await.map(Json).map_err(|e| { error!("list: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn create_deal(State(s): State<AppState>, Json(req): Json<CreateDealReq>) -> Result<Json<Deal>, StatusCode> {
    let g = s.read().await;
    g.create_deal(req).await.map(Json).map_err(|e| { error!("deal: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn advance_deal(State(s): State<AppState>, Path(id): Path<String>) -> Result<Json<Deal>, StatusCode> {
    let g = s.read().await;
    g.advance_deal(&id).await.map(Json).map_err(|e| { error!("advance: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn forecast(State(s): State<AppState>) -> Result<Json<PipelineForecast>, StatusCode> {
    let g = s.read().await;
    g.forecast().await.map(Json).map_err(|e| { error!("forecast: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn audit(State(s): State<AppState>) -> Result<Json<Vec<AuditLog>>, StatusCode> {
    let g = s.read().await;
    g.auditor.list(Some("gtm-engine"), 500).await
        .map(Json).map_err(|e| { error!("audit: {}", e); StatusCode::INTERNAL_SERVER_ERROR })
}

async fn events(State(s): State<AppState>) -> Json<Vec<Event>> {
    Json(s.read().await.bus.recent(100).await)
}

async fn signals(State(s): State<AppState>) -> Result<Json<Vec<TrajectorySignal>>, StatusCode> {
    let g = s.read().await;
    let rows: Vec<TrajectorySignal> = sqlx::query_as(
        "SELECT * FROM trajectory_signals WHERE source_agent = 'gtm-engine' ORDER BY ts DESC LIMIT 500"
    ).fetch_all(&g.pool).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(rows))
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let cfg = Config::from_env("gtm-engine")?;
    let auth_state = Arc::new(AuthState::new(cfg.api_token.clone()));
    let engine = Arc::new(RwLock::new(GtmEngine::new(cfg).await?));

    // Background nurture
    let nurture_engine = engine.clone();
    tokio::spawn(async move { GtmEngine::nurture_loop(nurture_engine).await });

    let cors = cors_layer(&engine.read().await.cfg.cors_origin);

    let public = Router::new().route("/health", get(health));

    let protected = Router::new()
        .route("/accounts", post(ingest_account).get(list_accounts))
        .route("/deals", post(create_deal))
        .route("/deals/{id}/advance", post(advance_deal))
        .route("/pipeline/forecast", get(forecast))
        .route("/audit", get(audit))
        .route("/events", get(events))
        .route("/signals", get(signals))
        .layer(middleware::from_fn_with_state(auth_state.clone(), bearer_auth));

    let app = Router::new()
        .merge(public)
        .merge(protected)
        .layer(cors)
        .layer(middleware::from_fn(request_logger))
        .with_state(engine);

    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".into());
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{}", port)).await?;
    info!("GTM Engine v1.0 (Clow) on :{}", port);

    axum::serve(listener, app)
        .with_graceful_shutdown(graceful_shutdown_signal())
        .await?;
    Ok(())
}
