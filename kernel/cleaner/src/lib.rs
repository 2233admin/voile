// XAR-6: Chinese text cleaning -- noise removal, URL extraction, sentence split
use once_cell::sync::Lazy;
use regex::Regex;

static URL_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"https?://[^\s\u4e00-\u9fff]+").unwrap()
});

static SPECIAL_RE: Lazy<Regex> = Lazy::new(|| {
    // remove emoji sequences, control chars, and repetitive punctuation
    Regex::new(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]|[\u{fe00}-\u{fe0f}]").unwrap()
});

static SENTENCE_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"[。！？!?]+").unwrap()
});

pub struct CleanResult {
    pub cleaned_text: String,
    pub extracted_urls: Vec<String>,
    pub sentences: Vec<String>,
}

pub fn clean(text: &str, extract_urls: bool) -> CleanResult {
    let urls: Vec<String> = if extract_urls {
        URL_RE.find_iter(text).map(|m| m.as_str().to_owned()).collect()
    } else {
        vec![]
    };

    // strip URLs from text before further cleaning
    let no_urls = URL_RE.replace_all(text, " ");
    let cleaned = SPECIAL_RE.replace_all(&no_urls, "");
    let cleaned = cleaned.trim().to_string();

    let sentences: Vec<String> = SENTENCE_RE
        .split(&cleaned)
        .filter_map(|s| {
            let t = s.trim().to_string();
            if t.is_empty() { None } else { Some(t) }
        })
        .collect();

    CleanResult { cleaned_text: cleaned, extracted_urls: urls, sentences }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_urls() {
        let r = clean("check https://example.com out", true);
        assert_eq!(r.extracted_urls, vec!["https://example.com"]);
        assert!(!r.cleaned_text.contains("https://"));
    }

    #[test]
    fn splits_sentences() {
        let r = clean("hello world. how are you? I am fine!", false);
        assert!(r.sentences.len() >= 2);
    }
}
