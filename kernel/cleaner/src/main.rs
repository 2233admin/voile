// gRPC server entrypoint for TextCleaner (XAR-6)
use tonic::{transport::Server, Request, Response, Status};
use tracing::info;
use voile_cleaner::clean;

// Generated from proto -- run `cargo build` after adding build.rs
pub mod kernel {
    tonic::include_proto!("voile.kernel.v1");
}

use kernel::{
    text_cleaner_server::{TextCleaner, TextCleanerServer},
    CleanBatchRequest, CleanBatchResponse, CleanRequest, CleanResponse,
};

#[derive(Default)]
struct CleanerService;

#[tonic::async_trait]
impl TextCleaner for CleanerService {
    async fn clean(&self, req: Request<CleanRequest>) -> Result<Response<CleanResponse>, Status> {
        let r = req.into_inner();
        let result = clean(&r.text, r.extract_urls);
        Ok(Response::new(CleanResponse {
            cleaned_text: result.cleaned_text,
            extracted_urls: result.extracted_urls,
            sentences: result.sentences,
        }))
    }

    async fn clean_batch(
        &self,
        req: Request<CleanBatchRequest>,
    ) -> Result<Response<CleanBatchResponse>, Status> {
        let items = req.into_inner().items;
        let processed = items.len() as u32;
        let results = items
            .into_iter()
            .map(|r| {
                let res = clean(&r.text, r.extract_urls);
                CleanResponse {
                    cleaned_text: res.cleaned_text,
                    extracted_urls: res.extracted_urls,
                    sentences: res.sentences,
                }
            })
            .collect();
        Ok(Response::new(CleanBatchResponse { items: results, processed }))
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().with_env_filter("info").init();
    let addr = "[::]:50051".parse()?;
    info!("TextCleaner gRPC listening on {addr}");
    Server::builder()
        .add_service(TextCleanerServer::new(CleanerService::default()))
        .serve(addr)
        .await?;
    Ok(())
}
