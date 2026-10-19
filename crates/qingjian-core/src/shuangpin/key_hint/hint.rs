//! 一张键位提示键盘：三排字母键，按方案标出声母、韵母与下一键的去向。

use super::{KeyCap, KeyState};
use crate::shuangpin::Scheme;

/// 主键区三排，`;` 只在用到它的方案里出现。
const ROWS: [&str; 3] = ["qwertyuiop", "asdfghjkl;", "zxcvbnm"];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyHint {
    pub scheme: Scheme,

    /// 落单、等着配第二键的那个键。
    pub pending: Option<char>,

    /// 敲出了配不成音节的键（解码留下了尾巴）：多半是记不清键位，自动模式下立刻弹出。
    pub stuck: bool,

    pub rows: Vec<Vec<KeyCap>>,
}

impl KeyHint {
    /// 按缓冲区里敲过的双拼键算：末尾落单一键时标出它能配的第二键，否则是空闲的整张键位表。
    pub fn for_keys(scheme: Scheme, keys: &str) -> Self {
        let decoded = scheme.decode(keys);
        let pending = decoded
            .pending_initial()
            .then(|| {
                decoded
                    .units()
                    .last()
                    .and_then(|unit| unit.keys.chars().next())
            })
            .flatten();
        Self {
            stuck: !decoded.tail().is_empty(),
            ..Self::new(scheme, pending)
        }
    }

    pub fn new(scheme: Scheme, pending: Option<char>) -> Self {
        let rows = ROWS
            .iter()
            .map(|row| {
                row.chars()
                    .filter(|key| scheme.is_key(*key))
                    .map(|key| KeyCap {
                        key,
                        initial: scheme.initial(key).filter(|initial| initial.len() > 1),
                        finals: scheme
                            .finals(key)
                            .iter()
                            .map(|final_| final_.replace('v', "ü"))
                            .collect(),
                        state: state(scheme, pending, key),
                    })
                    .collect()
            })
            .collect();
        Self {
            scheme,
            pending,
            stuck: false,
            rows,
        }
    }
}

fn state(scheme: Scheme, pending: Option<char>, key: char) -> KeyState {
    let Some(first) = pending else {
        return KeyState::Idle;
    };
    match scheme.syllable(first, key) {
        // 双写的零声母（`aa`、`ee`）第二键就是自己，标成音节而不是「刚敲下」
        Some(syllable) => KeyState::Next(syllable),
        None if key == first => KeyState::Pressed,
        None => KeyState::Unavailable,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cap(hint: &KeyHint, key: char) -> &KeyCap {
        hint.rows
            .iter()
            .flatten()
            .find(|cap| cap.key == key)
            .unwrap()
    }

    #[test]
    fn idle_board_lists_scheme_layout() {
        let hint = KeyHint::for_keys(Scheme::Xiaohe, "");
        assert_eq!(hint.pending, None);
        assert_eq!(
            hint.rows.iter().map(Vec::len).collect::<Vec<_>>(),
            [10, 9, 7]
        );
        assert_eq!(cap(&hint, 'v').initial, Some("zh"));
        assert_eq!(cap(&hint, 'v').finals, ["ui", "ü"]);
        assert_eq!(cap(&hint, 't').finals, ["üe", "ue"]);
        assert_eq!(cap(&hint, 'b').initial, None);
        assert!(
            hint.rows
                .iter()
                .flatten()
                .all(|cap| cap.state == KeyState::Idle)
        );
    }

    #[test]
    fn semicolon_only_where_scheme_uses_it() {
        assert!(
            KeyHint::new(Scheme::Microsoft, None).rows[1]
                .iter()
                .any(|c| c.key == ';')
        );
        assert!(
            !KeyHint::new(Scheme::Xiaohe, None).rows[1]
                .iter()
                .any(|c| c.key == ';')
        );
    }

    #[test]
    fn pending_initial_marks_reachable_syllables() {
        let hint = KeyHint::for_keys(Scheme::Xiaohe, "nihcv");
        assert_eq!(hint.pending, Some('v'));
        assert_eq!(cap(&hint, 's').state, KeyState::Next("zhong".to_owned()));
        assert_eq!(cap(&hint, 'i').state, KeyState::Next("zhi".to_owned()));
        assert_eq!(cap(&hint, 'b').state, KeyState::Unavailable);
    }

    #[test]
    fn complete_syllables_leave_board_idle() {
        let hint = KeyHint::for_keys(Scheme::Xiaohe, "nihc");
        assert_eq!(hint.pending, None);
        assert!(!hint.stuck);
    }

    #[test]
    fn impossible_pair_is_stuck() {
        // 小鹤 `vb` 拼不出音节
        assert!(KeyHint::for_keys(Scheme::Xiaohe, "nivb").stuck);
    }

    #[test]
    fn zero_initial_vowel_waits_for_second_key() {
        let hint = KeyHint::for_keys(Scheme::Xiaohe, "a");
        assert_eq!(hint.pending, Some('a'));
        assert_eq!(cap(&hint, 'a').state, KeyState::Next("a".to_owned()));
        assert_eq!(cap(&hint, 'h').state, KeyState::Next("ang".to_owned()));
    }
}
