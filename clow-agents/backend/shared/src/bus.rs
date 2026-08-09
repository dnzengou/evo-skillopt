use serde::{Deserialize, Serialize};
use tokio::sync::{broadcast, RwLock};
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub id: String,
    pub topic: String,
    pub payload: serde_json::Value,
    pub ts: chrono::DateTime<chrono::Utc>,
    pub source: String,
}

pub struct KafCa {
    tx: broadcast::Sender<Event>,
    log: Arc<RwLock<Vec<Event>>>,
    cap: usize,
}

impl KafCa {
    pub fn new(cap: usize) -> Self {
        let (tx, _) = broadcast::channel(cap);
        Self { tx, log: Arc::new(RwLock::new(vec![])), cap }
    }

    pub async fn emit(&self, e: Event) {
        let _ = self.tx.send(e.clone());
        let mut log = self.log.write().await;
        log.push(e);
        // Ring buffer: trim to cap
        if log.len() > self.cap {
            let excess = log.len() - self.cap;
            log.drain(0..excess);
        }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.tx.subscribe()
    }

    pub async fn recent(&self, n: usize) -> Vec<Event> {
        let log = self.log.read().await;
        log.iter().rev().take(n).cloned().collect()
    }
}
