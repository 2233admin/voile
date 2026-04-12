// XAR-6: Chinese text cleaning -- noise removal, URL extraction, sentence split
use once_cell::sync::Lazy;
use regex::Regex;

static URL_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"https?://[^\s\u4e00-\u9fff]+").unwrap()
});

static EMOJI_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]").unwrap()
});

static SYSTEM_MSG_RE: Lazy<Regex> = Lazy::new(|| {
    // QQ/WeChat bracket system messages: [图片] [语音] [视频] [文件] [表情] etc.
    Regex::new(r"\[(?:图片|语音|视频|文件|表情|链接|红包|转账|位置|名片|合并转发消息|动画表情|骰子|石头剪刀布|猜拳|抖一抖|[^\]]{1,20})\]").unwrap()
});

static CONTROL_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]|[\u{fe00}-\u{fe0f}]").unwrap()
});

static MULTI_SPACE_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"[ \t]{2,}").unwrap()
});

static SENTENCE_RE: Lazy<Regex> = Lazy::new(|| {
    // Split on: 。！？!? and ellipsis (……/...)
    Regex::new(r"[。！？!?]+|\.{3,}|\u{2026}{1,2}").unwrap()
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

    // 1. strip URLs
    let s = URL_RE.replace_all(text, " ");
    // 2. remove emoji
    let s = EMOJI_RE.replace_all(&s, "");
    // 3. remove QQ/WeChat system messages
    let s = SYSTEM_MSG_RE.replace_all(&s, "");
    // 4. remove control chars / variation selectors
    let s = CONTROL_RE.replace_all(&s, "");
    // 5. merge consecutive spaces/tabs into one
    let s = MULTI_SPACE_RE.replace_all(&s, " ");
    let cleaned = s.trim().to_string();

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

    #[test]
    fn test_removes_emoji() {
        let r = clean("hello\u{1F600}world\u{2614}end", false);
        assert!(!r.cleaned_text.contains('\u{1F600}'));
        assert!(!r.cleaned_text.contains('\u{2614}'));
        assert!(r.cleaned_text.contains("hello"));
        assert!(r.cleaned_text.contains("world"));
    }

    #[test]
    fn test_removes_system_msgs() {
        let r = clean("[图片]hello", false);
        assert_eq!(r.cleaned_text, "hello");
    }

    #[test]
    fn test_merges_spaces() {
        let r = clean("hello   world", false);
        assert_eq!(r.cleaned_text, "hello world");
    }

    #[test]
    fn test_splits_on_ellipsis() {
        let r = clean("\u{597d}\u{7684}\u{2026}\u{2026}\u{7136}\u{540e}\u{5462}", false);
        assert_eq!(r.sentences.len(), 2);
    }
}
