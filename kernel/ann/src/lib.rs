// XAR-7: HNSW-based ANN engine for message embedding search
use anyhow::Result;
use std::collections::HashMap;

pub struct VectorStore {
    // hnsw_rs index lives here in the real impl
    // placeholder for skeleton -- replace with hnsw_rs::Hnsw in XAR-7 full impl
    records: Vec<(String, Vec<f32>, HashMap<String, String>)>,
}

impl VectorStore {
    pub fn new() -> Self {
        Self { records: vec![] }
    }

    pub fn insert(&mut self, id: String, vector: Vec<f32>, metadata: HashMap<String, String>) -> Result<()> {
        // TODO: delegate to HNSW index
        self.records.retain(|(rid, _, _)| rid != &id);
        self.records.push((id, vector, metadata));
        Ok(())
    }

    pub fn search(&self, query: &[f32], top_k: usize, threshold: f32) -> Vec<(String, f32, HashMap<String, String>)> {
        let mut scored: Vec<_> = self
            .records
            .iter()
            .map(|(id, vec, meta)| (id.clone(), cosine(query, vec), meta.clone()))
            .filter(|(_, score, _)| *score >= threshold)
            .collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        scored.truncate(top_k);
        scored
    }

    pub fn delete(&mut self, id: &str) -> bool {
        let before = self.records.len();
        self.records.retain(|(rid, _, _)| rid != id);
        self.records.len() < before
    }
}

impl Default for VectorStore {
    fn default() -> Self { Self::new() }
}

fn cosine(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() { return 0.0; }
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let na: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let nb: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if na == 0.0 || nb == 0.0 { 0.0 } else { dot / (na * nb) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn insert_and_search() {
        let mut store = VectorStore::new();
        store.insert("a".into(), vec![1.0, 0.0], HashMap::new()).unwrap();
        store.insert("b".into(), vec![0.0, 1.0], HashMap::new()).unwrap();
        let hits = store.search(&[1.0, 0.0], 1, 0.9);
        assert_eq!(hits[0].0, "a");
    }

    #[test]
    fn delete_removes_record() {
        let mut store = VectorStore::new();
        store.insert("x".into(), vec![1.0], HashMap::new()).unwrap();
        assert!(store.delete("x"));
        assert!(store.search(&[1.0], 10, 0.0).is_empty());
    }
}
