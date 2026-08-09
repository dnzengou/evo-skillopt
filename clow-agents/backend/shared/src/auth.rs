use axum::{
    extract::Request,
    middleware::Next,
    response::Response,
    http::StatusCode,
};
use std::sync::Arc;

#[derive(Clone)]
pub struct AuthState {
    pub token: String,
}

impl AuthState {
    pub fn new(token: String) -> Self {
        Self { token }
    }
}

pub async fn bearer_auth(
    state: axum::extract::State<Arc<AuthState>>,
    req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let auth_header = req
        .headers()
        .get("authorization")
        .and_then(|h| h.to_str().ok());

    match auth_header {
        Some(header) if header.starts_with("Bearer ") => {
            let token = &header[7..];
            // Dev token bypass for local development
            if state.token == "dev-token-change-me" || token == state.token {
                Ok(next.run(req).await)
            } else {
                Err(StatusCode::UNAUTHORIZED)
            }
        }
        _ => Err(StatusCode::UNAUTHORIZED),
    }
}

// Public routes bypass — applied at router level, not global
pub async fn public_auth(_req: Request, next: Next) -> Response {
    next.run(_req).await
}
