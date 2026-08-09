use axum::{
    extract::Request,
    middleware::Next,
    response::Response,
    http::header::{HeaderName, AUTHORIZATION, CONTENT_TYPE},
};
use tower_http::cors::{Any, CorsLayer};
use std::time::Duration;
use tracing::info;

// CORS layer for dashboard integration
pub fn cors_layer(origin: &str) -> CorsLayer {
    let cors = CorsLayer::new()
        .allow_methods(Any)
        .allow_headers([AUTHORIZATION, CONTENT_TYPE, HeaderName::from_static("x-request-id")])
        .max_age(Duration::from_secs(86400));

    if origin == "*" {
        cors.allow_origin(Any)
    } else {
        let origins: Vec<_> = origin.split(',').map(|s| s.trim().parse().unwrap()).collect();
        cors.allow_origin(origins)
    }
}

// Request ID + logging middleware
pub async fn request_logger(req: Request, next: Next) -> Response {
    let method = req.method().clone();
    let path = req.uri().path().to_string();
    let request_id = uuid::Uuid::new_v4().to_string()[..8].to_string();

    let span = tracing::info_span!("http", %request_id, %method, %path);
    let _enter = span.enter();

    info!("=> {} {}", method, path);
    let start = std::time::Instant::now();
    let mut response = next.run(req).await;
    let duration = start.elapsed();
    let status = response.status();

    response.headers_mut().insert(
        HeaderName::from_static("x-request-id"),
        request_id.parse().unwrap(),
    );

    info!("<= {} {} | {} | {:?}", method, path, status, duration);
    response
}

// Graceful shutdown helper
pub async fn graceful_shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c().await.expect("ctrl+c handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => info!("SIGINT received, shutting down gracefully"),
        _ = terminate => info!("SIGTERM received, shutting down gracefully"),
    }
}
