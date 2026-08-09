use anyhow::Result;
use serde_json::json;

pub struct Notifier {
    slack: String,
    resend: String,
    pagerduty: String,
    http: reqwest::Client,
    from_email: String,
}

impl Notifier {
    pub fn new(slack: &str, resend: &str, pagerduty: &str) -> Self {
        Self {
            slack: slack.to_string(),
            resend: resend.to_string(),
            pagerduty: pagerduty.to_string(),
            http: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(10))
                .build()
                .unwrap(),
            from_email: "agents@deploy-flyio.io".to_string(),
        }
    }

    pub async fn slack(&self, msg: &str) -> Result<()> {
        if self.slack.is_empty() { return Ok(()); }
        self.http.post(&self.slack)
            .json(&json!({"text": msg}))
            .send().await?;
        Ok(())
    }

    pub async fn email(&self, to: &str, subj: &str, body: &str) -> Result<()> {
        if self.resend.is_empty() { return Ok(()); }
        self.http.post("https://api.resend.com/emails")
            .header("Authorization", format!("Bearer {}", self.resend))
            .json(&json!({
                "from": self.from_email,
                "to": [to],
                "subject": subj,
                "html": body
            }))
            .send().await?;
        Ok(())
    }

    pub async fn pagerduty(&self, msg: &str) -> Result<()> {
        if self.pagerduty.is_empty() { return Ok(()); }
        self.http.post("https://events.pagerduty.com/v2/enqueue")
            .json(&json!({
                "routing_key": self.pagerduty,
                "event_action": "trigger",
                "payload": {
                    "summary": msg,
                    "severity": "critical",
                    "source": "security-agent"
                }
            }))
            .send().await?;
        Ok(())
    }
}
