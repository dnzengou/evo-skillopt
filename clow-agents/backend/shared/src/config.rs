use anyhow::Result;

#[derive(Clone)]
pub struct Config {
    // Auth
    pub api_token: String,
    // Fly
    pub fly_token: String,
    // Notifications
    pub slack_webhook: String,
    pub resend_key: String,
    pub pagerduty_key: String,
    pub github_token: String,
    pub apollo_key: String,
    // LLM
    pub llm_api_key: String,
    pub llm_base_url: String,
    // Targets
    pub gtm_targets: Vec<String>,
    pub security_targets: Vec<String>,
    // CORS
    pub cors_origin: String,
    // Rate limiting (security-agent)
    pub rate_limit_per_minute: u32,
    // Database
    pub database_url: String,
}

impl Config {
    pub fn from_env(service: &str) -> Result<Self> {
        let gtm_targets = split_env("GTM_TARGETS");
        let security_targets = split_env("SECURITY_TARGETS");
        let db_path = std::env::var("DATABASE_URL")
            .unwrap_or_else(|_| format!("sqlite://{}.db", service));

        Ok(Self {
            api_token: std::env::var("API_TOKEN").unwrap_or_else(|_| "dev-token-change-me".into()),
            fly_token: std::env::var("FLY_TOKEN").unwrap_or_default(),
            slack_webhook: std::env::var("SLACK_WEBHOOK").unwrap_or_default(),
            resend_key: std::env::var("RESEND_KEY").unwrap_or_default(),
            pagerduty_key: std::env::var("PAGERDUTY_KEY").unwrap_or_default(),
            github_token: std::env::var("GITHUB_TOKEN").unwrap_or_default(),
            apollo_key: std::env::var("APOLLO_KEY").unwrap_or_default(),
            llm_api_key: std::env::var("LLM_API_KEY").unwrap_or_default(),
            llm_base_url: std::env::var("LLM_BASE_URL").unwrap_or_default(),
            gtm_targets,
            security_targets,
            cors_origin: std::env::var("CORS_ORIGIN").unwrap_or_else(|_| "*".into()),
            rate_limit_per_minute: std::env::var("RATE_LIMIT_PER_MINUTE")
                .unwrap_or_else(|_| "10".into())
                .parse()
                .unwrap_or(10),
            database_url: db_path,
        })
    }
}

fn split_env(key: &str) -> Vec<String> {
    std::env::var(key)
        .unwrap_or_default()
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect()
}
