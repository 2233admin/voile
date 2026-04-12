// gRPC server entrypoint for VectorIndex (XAR-7)
use std::collections::HashMap;
use std::sync::Mutex;
use tonic::{transport::Server, Request, Response, Status};
use tracing::info;
use voile_ann::VectorStore;

pub mod kernel {
    tonic::include_proto!("voile.kernel.v1");
}

use kernel::{
    vector_index_server::{VectorIndex, VectorIndexServer},
    BatchInsertRequest, BatchInsertResponse, DeleteRequest, DeleteResponse,
    InsertRequest, InsertResponse, SearchRequest, SearchResponse,
};

struct IndexService {
    store: Mutex<VectorStore>,
}

impl IndexService {
    fn new() -> Self {
        Self { store: Mutex::new(VectorStore::new()) }
    }
}

#[tonic::async_trait]
impl VectorIndex for IndexService {
    async fn insert(&self, req: Request<InsertRequest>) -> Result<Response<InsertResponse>, Status> {
        let r = req.into_inner();
        let vec = r.vector.map(|v| v.values).unwrap_or_default();
        let meta: HashMap<String, String> = r.metadata;
        self.store.lock().unwrap().insert(r.id, vec, meta).map_err(|e| Status::internal(e.to_string()))?;
        Ok(Response::new(InsertResponse { ok: true }))
    }

    async fn batch_insert(&self, req: Request<BatchInsertRequest>) -> Result<Response<BatchInsertResponse>, Status> {
        let items = req.into_inner().items;
        let (mut inserted, mut failed) = (0u32, 0u32);
        let mut store = self.store.lock().unwrap();
        for item in items {
            let vec = item.vector.map(|v| v.values).unwrap_or_default();
            match store.insert(item.id, vec, item.metadata) {
                Ok(_) => inserted += 1,
                Err(_) => failed += 1,
            }
        }
        Ok(Response::new(BatchInsertResponse { inserted, failed }))
    }

    async fn search(&self, req: Request<SearchRequest>) -> Result<Response<SearchResponse>, Status> {
        let r = req.into_inner();
        let query = r.query.map(|v| v.values).unwrap_or_default();
        let hits = self.store.lock().unwrap().search(&query, r.top_k as usize, r.threshold);
        let results = hits.into_iter().map(|(id, score, metadata)| kernel::SearchResult { id, score, metadata }).collect();
        Ok(Response::new(SearchResponse { results }))
    }

    async fn delete(&self, req: Request<DeleteRequest>) -> Result<Response<DeleteResponse>, Status> {
        let ok = self.store.lock().unwrap().delete(&req.into_inner().id);
        Ok(Response::new(DeleteResponse { ok }))
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().with_env_filter("info").init();
    let addr = "[::]:50052".parse()?;
    info!("VectorIndex gRPC listening on {addr}");
    Server::builder()
        .add_service(VectorIndexServer::new(IndexService::new()))
        .serve(addr)
        .await?;
    Ok(())
}
