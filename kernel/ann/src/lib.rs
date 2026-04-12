// XAR-7: HNSW-based ANN engine for message embedding search
use anyhow::Result;
use std::collections::HashMap;

use hnsw_rs::prelude::*;

pub struct VectorStore {
    hnsw: Hnsw<'static, f32, DistCosine>,
    id_map: HashMap<usize, (String, HashMap<String, String>)>, // usize -> (str_id, metadata)
    str_to_idx: HashMap<String, usize>,                        // str_id -> usize (for delete)
    deleted: std::collections::HashSet<usize>,                 // soft-deleted ids
    next_id: usize,
    dim: usize,
}

impl VectorStore {
    /// `max_elements` is a capacity hint; the index grows dynamically.
    pub fn new() -> Self {
        Self::with_capacity(1024)
    }

    pub fn with_capacity(max_elements: usize) -> Self {
        // max_nb_connection=16, max_layer=16, ef_construction=200
        let hnsw: Hnsw<'static, f32, DistCosine> =
            Hnsw::new(16, max_elements, 16, 200, DistCosine {});
        Self {
            hnsw,
            id_map: HashMap::new(),
            str_to_idx: HashMap::new(),
            deleted: std::collections::HashSet::new(),
            next_id: 0,
            dim: 0,
        }
    }

    pub fn insert(&mut self, id: String, vector: Vec<f32>, metadata: HashMap<String, String>) -> Result<()> {
        // If id already exists, soft-delete the old entry first
        if let Some(&old_idx) = self.str_to_idx.get(&id) {
            self.deleted.insert(old_idx);
            self.id_map.remove(&old_idx);
        }

        let idx = self.next_id;
        self.next_id += 1;

        if self.dim == 0 && !vector.is_empty() {
            self.dim = vector.len();
        }

        self.hnsw.insert((&vector, idx));
        self.id_map.insert(idx, (id.clone(), metadata));
        self.str_to_idx.insert(id, idx);

        Ok(())
    }

    /// Returns `(str_id, cosine_similarity, metadata)` sorted descending by similarity.
    /// `threshold` is applied to cosine similarity (0.0–1.0).
    pub fn search(&self, query: &[f32], top_k: usize, threshold: f32) -> Vec<(String, f32, HashMap<String, String>)> {
        if self.id_map.is_empty() {
            return vec![];
        }
        // Request more candidates to account for soft-deleted entries
        let fetch_k = (top_k + self.deleted.len()).max(top_k * 2);
        let ef_search = fetch_k.max(16);

        let neighbours = self.hnsw.search(query, fetch_k, ef_search);

        let mut results: Vec<(String, f32, HashMap<String, String>)> = neighbours
            .into_iter()
            .filter_map(|nb| {
                let idx = nb.d_id;
                if self.deleted.contains(&idx) {
                    return None;
                }
                let (str_id, meta) = self.id_map.get(&idx)?;
                // hnsw_rs DistCosine returns dissimilarity; convert to similarity
                let similarity = 1.0_f32 - nb.distance;
                if similarity >= threshold {
                    Some((str_id.clone(), similarity, meta.clone()))
                } else {
                    None
                }
            })
            .collect();

        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(top_k);
        results
    }

    /// Soft-deletes an entry. Returns true if the id existed.
    pub fn delete(&mut self, id: &str) -> bool {
        if let Some(idx) = self.str_to_idx.remove(id) {
            self.deleted.insert(idx);
            self.id_map.remove(&idx);
            true
        } else {
            false
        }
    }
}

impl Default for VectorStore {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn unit(v: &[f32]) -> Vec<f32> {
        let norm: f32 = v.iter().map(|x| x * x).sum::<f32>().sqrt();
        v.iter().map(|x| x / norm).collect()
    }

    #[test]
    fn insert_and_search() {
        let mut store = VectorStore::new();
        store.insert("a".into(), unit(&[1.0, 0.0]), HashMap::new()).unwrap();
        store.insert("b".into(), unit(&[0.0, 1.0]), HashMap::new()).unwrap();
        let hits = store.search(&unit(&[1.0, 0.0]), 1, 0.9);
        assert_eq!(hits.len(), 1, "expected 1 hit, got {:?}", hits);
        assert_eq!(hits[0].0, "a");
    }

    #[test]
    fn delete_removes_record() {
        let mut store = VectorStore::new();
        store.insert("x".into(), unit(&[1.0, 0.0]), HashMap::new()).unwrap();
        assert!(store.delete("x"));
        let results = store.search(&unit(&[1.0, 0.0]), 10, 0.0);
        assert!(results.is_empty(), "expected empty after delete, got {:?}", results);
    }
}
